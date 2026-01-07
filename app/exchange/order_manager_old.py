from app.exchange.client import ExchangeClient
from app.exchange.factory import ExchangeFactory
from app.models.order import OrderRequest, OrderResponse
from app.utils.indicators import get_atr_for_symbol
from app.config.settings import settings
from app.utils.logger import logger


class OrderManager:
    """Управление ордерами на бирже"""
    
    def __init__(self):
        self.clients = {}  # Кэш клиентов по биржам
    
    async def _get_client(self, exchange_name: str) -> ExchangeClient:
        """Получение или создание клиента для биржи"""
        if exchange_name not in self.clients:
            client = ExchangeFactory.create_client(exchange_name)
            await client.load_markets()
            self.clients[exchange_name] = client
        return self.clients[exchange_name]
    
    async def execute_trade(self, order_request: OrderRequest) -> OrderResponse:
        """
        Выполнение торговой операции
        
        Args:
            order_request: запрос на создание ордера
        
        Returns:
            OrderResponse с результатами
        """
        import time
        start_time = time.time()
        try:
            client = await self._get_client(order_request.exchange)
            
            # Форматируем символ для биржи
            symbol = ExchangeFactory.get_symbol_format(
                order_request.exchange,
                order_request.symbol,
                order_request.contract_type
            )
            
            logger.info(
                f"Выполнение сделки: {symbol}, {order_request.side}, "
                f"size={order_request.amount} USDT, leverage={order_request.leverage}"
            )

            # ---- Проверяем и устанавливаем плечо ----
            try:
                market = client.client.market(symbol)

                leverage_to_set = order_request.leverage
                max_leverage = (
                    market.get("limits", {})
                    .get("leverage", {})
                    .get("max")
                )

                if max_leverage and leverage_to_set > max_leverage:
                    logger.warning(
                        f"Запрошенное плечо {leverage_to_set} превышает допустимое "
                        f"для {symbol}. Используем {max_leverage}"
                    )
                    leverage_to_set = max_leverage

                logger.info(f"Устанавливаем плечо {leverage_to_set} для {symbol}")
                await client.set_leverage(symbol, leverage_to_set)

            except Exception as e:
                logger.error(f"Не удалось установить плечо для {symbol}: {e}")

            # Устанавливаем кредитное плечо
            # await client.set_leverage(symbol, order_request.leverage)
            
            # Рассчитываем размер позиции
            # amount всегда интерпретируется как сумма в USDT
            # Для всех бирж конвертируем сумму в USDT в количество контрактов
            # Для Binance market ордеров можно использовать quoteOrderQty (альтернативный способ)
            order_params = {}
            usdt_amount = order_request.amount  # Сумма в USDT
            if order_request.exchange == "bybit":
                if order_request.side.lower() == "buy":
                    order_params["positionIdx"] = 1
                else:
                    order_params["positionIdx"] = 2
            
            # Получаем цену входа для конвертации
            entry_price_for_calc = order_request.entry_price
            if not entry_price_for_calc:
                # Если цены нет (для market ордеров), получаем текущую цену
                try:
                    ticker = await client.client.fetch_ticker(symbol)
                    entry_price_for_calc = ticker['last']
                except Exception as e:
                    logger.warning(f"Не удалось получить текущую цену для {symbol}: {e}, используем цену из алерта")
                    entry_price_for_calc = order_request.entry_price
            
            if order_request.exchange == "binance" and settings.order_type == "market":
                # Для Binance market ордеров можно использовать quoteOrderQty для указания суммы в USDT
                order_params = {'quoteOrderQty': usdt_amount}  # Размер в USDT
                # Для Binance при использовании quoteOrderQty amount не используется, но CCXT может требовать его
                # Устанавливаем минимальное значение
                order_amount = 0.001  # Минимальное значение, реальный размер берется из quoteOrderQty
            else:
                # Для всех остальных бирж (Bybit, OKX, Bitget) и Binance limit ордеров
                # конвертируем сумму в USDT в количество контрактов
                # Для фьючерсов USDT-M: количество_контрактов = сумма_USDT / (цена * размер_контракта)
                # Обычно размер контракта = 1 для USDT-M, но проверим через markets
                if entry_price_for_calc:
                    # Получаем размер контракта из markets (обычно 1 для USDT-M)
                    contract_size = 1.0  # По умолчанию для USDT-M
                    try:
                        market = client.client.market(symbol)
                        if market and 'contractSize' in market:
                            contract_size = float(market['contractSize'])
                    except Exception as e:
                        logger.debug(f"Не удалось получить размер контракта для {symbol}: {e}, используем 1.0")
                    
                    # Конвертируем сумму в USDT в количество контрактов
                    # Для USDT-M фьючерсов: количество = сумма_USDT / (цена * размер_контракта)
                    # Обычно contract_size = 1, поэтому: количество = сумма_USDT / цена
                    order_amount = usdt_amount / (entry_price_for_calc * contract_size)
                    logger.info(f"Конвертация размера: {usdt_amount} USDT -> {order_amount:.6f} контрактов (цена: {entry_price_for_calc}, размер контракта: {contract_size})")
                else:
                    # Если не удалось получить цену, используем amount как есть (fallback)
                    logger.warning(f"Не удалось получить цену для конвертации, используем amount как есть: {usdt_amount}")
                    order_amount = usdt_amount
            
            # Создаем ордер для входа (market или limit в зависимости от настроек)
            actual_entry_price = None
            
            if settings.order_type == "limit":
                # Limit ордер - используем цену из алерта
                if not order_request.entry_price:
                    raise ValueError("Для limit ордера требуется entry_price")
                
                entry_order = await client.create_limit_order(
                    symbol=symbol,
                    side=order_request.side,
                    amount=order_amount,
                    price=order_request.entry_price,
                    params=order_params if order_params else None
                )
                actual_entry_price = order_request.entry_price
                logger.info(f"Создан limit ордер: {entry_order['id']} для {symbol} по цене {actual_entry_price}")
                # Для limit ордера SL/TP уже рассчитаны на основе цены из алерта, пересчет не нужен
            else:
                # Market ордер - исполняется по текущей рыночной цене
                entry_order = await client.create_market_order(
                    symbol=symbol,
                    side=order_request.side,
                    amount=order_amount,
                    params=order_params if order_params else None
                )
                
                # Получаем реальную цену исполнения market ордера
                actual_entry_price = entry_order.get('price') or entry_order.get('average')
                if not actual_entry_price:
                    # Если цена не в ордере, получаем текущую цену
                    try:
                        ticker = await client.client.fetch_ticker(symbol)
                        actual_entry_price = ticker['last']
                    except:
                        # Используем цену из алерта как fallback
                        actual_entry_price = order_request.entry_price if order_request.entry_price else None
                
                logger.info(f"Создан market ордер: {entry_order['id']} для {symbol}, реальная цена входа: {actual_entry_price}")
                
                # Для market ордера пересчитываем SL/TP на основе реальной цены входа
                if actual_entry_price:
                    try:
                        atr = await get_atr_for_symbol(client, symbol)
                        # Пересчитываем SL/TP
                        if order_request.side == "buy":  # LONG
                            order_request.stop_loss = actual_entry_price - (atr * settings.stop_loss_rate)
                            order_request.take_profit = actual_entry_price + (atr * settings.take_profit_rate)
                        else:  # SHORT
                            order_request.stop_loss = actual_entry_price + (atr * settings.stop_loss_rate)
                            order_request.take_profit = actual_entry_price - (atr * settings.take_profit_rate)
                        logger.info(f"Пересчитаны уровни на основе реальной цены: entry={actual_entry_price:.4f}, SL={order_request.stop_loss:.4f}, TP={order_request.take_profit:.4f}")
                    except Exception as e:
                        logger.warning(f"Не удалось пересчитать SL/TP на основе реальной цены: {e}, используем расчетные значения")
            
            logger.info(f"Позиция открыта: {entry_order['id']}, цена входа: {actual_entry_price}")
            
            # Устанавливаем TP/SL
            stop_loss_order = None
            take_profit_order = None
            
            # Определяем сторону для закрытия позиции
            stop_side = "sell" if order_request.side == "buy" else "buy"
            take_profit_side = stop_side
            
            # Для limit ордеров всегда используем отдельные ордера (позиция еще не открыта)
            # Для market ордеров на Bybit можно попробовать установить на позицию
            use_position_tp_sl = (
                settings.order_type == "market" and 
                order_request.exchange == "bybit"
            )
            
            if use_position_tp_sl:
                # Для market ордеров на Bybit пытаемся установить TP/SL на позицию
                try:
                    result = await client.set_position_tp_sl(
                        symbol=symbol,
                        stop_loss=order_request.stop_loss,
                        take_profit=order_request.take_profit
                    )
                    if result:
                        logger.info(f"TP/SL установлены на позицию {symbol}: SL={order_request.stop_loss}, TP={order_request.take_profit}")
                        stop_loss_order = {"id": "position_sl"}
                        take_profit_order = {"id": "position_tp"}
                except Exception as e:
                    logger.warning(f"Не удалось установить TP/SL на позицию: {e}, создаем отдельные ордера")
                    # Fallback: создаем отдельные ордера
                    use_position_tp_sl = False
            
            if not use_position_tp_sl:
                # Создаем отдельные ордера для TP/SL (для limit ордеров или если установка на позицию не удалась)
                # Для limit ордеров на Bybit позиция еще не открыта, поэтому TP/SL нельзя установить сразу
                is_limit_bybit = settings.order_type == "limit" and order_request.exchange == "bybit"
                
                if is_limit_bybit:
                    # Для limit ордеров на Bybit проверяем, исполнился ли ордер сразу
                    try:
                        order_status = await client.client.fetch_order(entry_order['id'], symbol)
                        if order_status.get('status') == 'closed' or order_status.get('filled', 0) > 0:
                            # Ордер уже исполнился, можно устанавливать TP/SL на позицию
                            try:
                                result = await client.set_position_tp_sl(
                                    symbol=symbol,
                                    stop_loss=order_request.stop_loss,
                                    take_profit=order_request.take_profit
                                )
                                if result:
                                    logger.info(f"TP/SL установлены на позицию {symbol} после исполнения limit ордера: SL={order_request.stop_loss}, TP={order_request.take_profit}")
                                    stop_loss_order = {"id": "position_sl"}
                                    take_profit_order = {"id": "position_tp"}
                                    use_position_tp_sl = True  # Пропускаем создание отдельных ордеров
                            except Exception as e:
                                logger.warning(f"Не удалось установить TP/SL на позицию после исполнения limit ордера: {e}")
                    except Exception as e:
                        logger.debug(f"Не удалось проверить статус limit ордера: {e}")
                
                if not use_position_tp_sl:
                    # Создаем стоп-лосс ордер (для других бирж или если установка на позицию не удалась)
                    if is_limit_bybit:
                        logger.warning(f"Для limit ордера на Bybit TP/SL не могут быть установлены до исполнения ордера. Рекомендуется использовать market ордер или установить TP/SL вручную после исполнения.")
                    else:
                        try:
                            stop_loss_order = await client.create_stop_loss_order(
                                symbol=symbol,
                                side=stop_side,
                                amount=order_amount,
                                price=order_request.stop_loss
                            )
                            logger.info(f"Стоп-лосс установлен: {stop_loss_order['id']}")
                        except Exception as e:
                            logger.error(f"Ошибка при установке стоп-лосс: {e}")
                    
                    # Создаем тейк-профит ордер
                    if is_limit_bybit:
                        # Для limit ордеров на Bybit не создаем тейк-профит, так как позиция еще не открыта
                        pass
                    else:
                        try:
                            take_profit_order = await client.create_take_profit_order(
                                symbol=symbol,
                                side=take_profit_side,
                                amount=order_amount,
                                price=order_request.take_profit
                            )
                            logger.info(f"Тейк-профит установлен: {take_profit_order['id']}")
                        except Exception as e:
                            logger.error(f"Ошибка при установке тейк-профита: {e}")
            
            execution_time = time.time() - start_time
            logger.info(f"⏱️ Время исполнения сделки: {execution_time:.2f} секунд")
            
            return OrderResponse(
                success=True,
                order_id=entry_order.get('id'),
                stop_loss_order_id=stop_loss_order.get('id') if stop_loss_order else None,
                take_profit_order_id=take_profit_order.get('id') if take_profit_order else None,
                message=f"Позиция успешно открыта (время: {execution_time:.2f}с)"
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Ошибка при выполнении сделки: {e} (время: {execution_time:.2f}с)")
            return OrderResponse(
                success=False,
                error=str(e)
            )
    
    async def calculate_stop_loss_take_profit(
        self,
        exchange_name: str,
        symbol: str,
        entry_price: float,
        direction: str,
        contract_type: str
    ) -> tuple[float, float]:
        """
        Расчет стоп-лосс и тейк-профит на основе ATR
        
        Returns:
            tuple[stop_loss, take_profit]
        """
        try:
            client = await self._get_client(exchange_name)
            
            # Форматируем символ для биржи
            formatted_symbol = ExchangeFactory.get_symbol_format(
                exchange_name,
                symbol,
                contract_type
            )
            
            # Получаем ATR
            atr = await get_atr_for_symbol(client, formatted_symbol)
            
            # Рассчитываем стоп-лосс и тейк-профит
            if direction == "LONG":
                stop_loss = entry_price - (atr * settings.stop_loss_rate)
                take_profit = entry_price + (atr * settings.take_profit_rate)
            else:  # SHORT
                stop_loss = entry_price + (atr * settings.stop_loss_rate)
                take_profit = entry_price - (atr * settings.take_profit_rate)
            
            logger.info(
                f"Рассчитаны уровни: entry={entry_price:.4f}, "
                f"ATR={atr:.4f}, SL={stop_loss:.4f}, TP={take_profit:.4f}"
            )
            
            return stop_loss, take_profit
            
        except Exception as e:
            logger.error(f"Ошибка при расчете SL/TP: {e}")
            raise
    
    async def close_all_connections(self):
        """Закрытие всех соединений"""
        for client in self.clients.values():
            await client.close()
        self.clients.clear()

