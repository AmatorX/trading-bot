import ccxt.async_support as ccxt
from typing import Optional
from app.config.settings import settings
from app.utils.logger import logger


class ExchangeClient:
    """Обертка над CCXT клиентом для работы с биржами"""
    
    def __init__(self, exchange_name: str, api_key: str, api_secret: str, 
                 passphrase: Optional[str] = None, sandbox: bool = False):
        self.exchange_name = exchange_name
        self.sandbox = sandbox
        
        # Создаем клиент CCXT
        exchange_class = getattr(ccxt, exchange_name)
        
        # Проверка наличия ключей
        if not api_key or not api_secret:
            raise ValueError(f"API ключи для {exchange_name} не указаны. Проверьте .env файл.")
        
        config = {
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',  # Фьючерсы
            }
        }
        
        # Для OKX и Bitget нужен passphrase
        if passphrase:
            config['password'] = passphrase
        
        # Sandbox режим
        if sandbox:
            config['sandbox'] = True
        
        self.client = exchange_class(config)
        logger.info(f"Инициализирован клиент {exchange_name} (sandbox={sandbox})")
    
    async def load_markets(self):
        """Загрузка рынков"""
        await self.client.load_markets()
        logger.info(f"Рынки загружены для {self.exchange_name}")
    
    async def get_balance(self):
        """Получение баланса"""
        try:
            balance = await self.client.fetch_balance()
            return balance
        except Exception as e:
            logger.error(f"Ошибка при получении баланса: {e}")
            raise
    
    async def set_leverage(self, symbol: str, leverage: int):
        """Установка кредитного плеча для символа"""
        try:
            # Для Bybit нужно использовать set_leverage с параметрами
            if self.exchange_name == "bybit":
                # Bybit требует установку плеча через set_leverage
                # Формат: set_leverage(leverage, symbol, params={'marginMode': 'isolated'})
                await self.client.set_leverage(leverage, symbol, params={'marginMode': 'isolated'})
            elif hasattr(self.client, 'set_leverage'):
                await self.client.set_leverage(leverage, symbol)
            elif hasattr(self.client, 'set_margin_mode'):
                # Некоторые биржи требуют установки режима маржи
                await self.client.set_margin_mode('isolated', symbol)
            else:
                logger.warning(f"Биржа {self.exchange_name} не поддерживает установку плеча через CCXT")
            logger.info(f"Установлено плечо {leverage}x для {symbol}")
        except Exception as e:
            error_str = str(e)
            # Если плечо уже установлено или не может быть изменено, это не критично
            if "not modified" in error_str.lower() or "110043" in error_str:
                logger.warning(f"Плечо не было изменено для {symbol} (возможно, уже установлено): {error_str}")
                # Не поднимаем исключение, продолжаем работу
            else:
                logger.error(f"Ошибка при установке плеча для {symbol}: {e}")
                raise

    async def create_market_order(self, symbol: str, side: str, amount: float, params: dict = None):
        """Создание market ордера"""
        try:
            params = params or {}

            # ---- BYBIT Hedge Mode FIX ----
            if self.exchange_name == "bybit":
                # normalize
                s = side.lower()
                if "buy" in s:
                    params.setdefault("positionIdx", 1)
                else:
                    params.setdefault("positionIdx", 2)

            order = await self.client.create_market_order(symbol, side, amount, params=params)
            logger.info(f"Создан market ордер: {order['id']} для {symbol}")
            return order

        except Exception as e:
            logger.error(f"Ошибка при создании market ордера: {e}")
            raise

    # async def create_market_order(self, symbol: str, side: str, amount: float, params: dict = None):
    #     """Создание market ордера"""
    #     try:
    #         if params:
    #             order = await self.client.create_market_order(symbol, side, amount, params=params)
    #         else:
    #             order = await self.client.create_market_order(symbol, side, amount)
    #         logger.info(f"Создан market ордер: {order['id']} для {symbol}")
    #         return order
    #     except Exception as e:
    #         logger.error(f"Ошибка при создании market ордера: {e}")
    #         raise
    
    async def create_limit_order(self, symbol: str, side: str, amount: float, price: float, params: dict = None):
        """Создание limit ордера"""
        try:
            if params:
                order = await self.client.create_limit_order(symbol, side, amount, price, params=params)
            else:
                order = await self.client.create_limit_order(symbol, side, amount, price)
            logger.info(f"Создан limit ордер: {order['id']} для {symbol} по цене {price}")
            return order
        except Exception as e:
            logger.error(f"Ошибка при создании limit ордера: {e}")
            raise
    
    async def create_stop_loss_order(self, symbol: str, side: str, amount: float, price: float):
        """Создание стоп-лосс ордера"""
        try:
            # Для Bybit нужен параметр triggerDirection
            if self.exchange_name == "bybit":
                # Для LONG позиции стоп-лосс срабатывает когда цена падает (descending)
                # Для SHORT позиции стоп-лосс срабатывает когда цена растет (ascending)
                # Но side уже указывает направление закрытия (sell для LONG, buy для SHORT)
                # triggerDirection определяет направление движения цены для срабатывания
                # Для стоп-лосс LONG: descending (цена падает)
                # Для стоп-лосс SHORT: ascending (цена растет)
                trigger_direction = "descending" if side == "sell" else "ascending"
                
                # Для Bybit фьючерсов используется тип 'Stop' с параметрами
                order = await self.client.create_order(
                    symbol=symbol,
                    type='Stop',  # Для Bybit фьючерсов
                    side=side,
                    amount=amount,
                    params={
                        'stopPrice': price,
                        'triggerDirection': trigger_direction,
                        'reduceOnly': True  # Только закрытие позиции
                    }
                )
            else:
                # Для других бирж
                order = await self.client.create_order(
                    symbol=symbol,
                    type='stop_market',
                    side=side,
                    amount=amount,
                    params={'stopPrice': price}
                )
            logger.info(f"Создан стоп-лосс ордер: {order['id']} для {symbol} по цене {price}")
            return order
        except Exception as e:
            logger.error(f"Ошибка при создании стоп-лосс ордера: {e}")
            raise
    
    async def create_take_profit_order(self, symbol: str, side: str, amount: float, price: float):
        """Создание тейк-профит ордера"""
        try:
            # Для Bybit фьючерсов тейк-профит устанавливается как limit ордер
            if self.exchange_name == "bybit":
                # Для Bybit используем limit ордер с reduceOnly
                order = await self.client.create_limit_order(
                    symbol=symbol,
                    side=side,
                    amount=amount,
                    price=price,
                    params={'reduceOnly': True}
                )
            else:
                # Для других бирж
                order = await self.client.create_limit_order(symbol, side, amount, price)
            logger.info(f"Создан тейк-профит ордер: {order['id']} для {symbol} по цене {price}")
            return order
        except Exception as e:
            logger.error(f"Ошибка при создании тейк-профит ордера: {e}")
            raise


    async def set_position_tp_sl(self, symbol: str, stop_loss: float = None, take_profit: float = None):
        """Установка TP/SL на позицию (для Bybit)"""
        try:
            if self.exchange_name != "bybit":
                logger.warning(f"Установка TP/SL на позицию не поддерживается для {self.exchange_name}")
                return None

            symbol_clean = symbol.replace('/', '').replace(':USDT', '')

            # ---- 🔍 Получаем открытую позицию чтобы понять positionIdx ----
            positions = await self.client.private_get_v5_position_list({
                "category": "linear",
                "symbol": symbol_clean
            })

            position = None
            if positions and positions["result"]["list"]:
                position = positions["result"]["list"][0]

            if not position:
                logger.warning(f"Нет открытой позиции для {symbol}, TP/SL не устанавливаем")
                return None

            position_idx = int(position["positionIdx"])

            params = {
                "category": "linear",
                "symbol": symbol_clean,
                "positionIdx": position_idx
            }

            if stop_loss:
                params["stopLoss"] = str(stop_loss)

            if take_profit:
                params["takeProfit"] = str(take_profit)

            result = await self.client.private_post_v5_position_trading_stop(params)

            logger.info(
                f"TP/SL установлены для {symbol} "
                f"(idx={position_idx}): SL={stop_loss}, TP={take_profit}"
            )

            return result

        except Exception as e:
            logger.error(f"Ошибка при установке TP/SL на позицию: {e}")
            return None

    # async def set_position_tp_sl(self, symbol: str, stop_loss: float = None, take_profit: float = None):
    #     """Установка TP/SL на позицию (для Bybit)"""
    #     try:
    #         if self.exchange_name == "bybit":
    #             # Для Bybit используем специальный метод для установки TP/SL на позицию
    #             # Формат символа для Bybit API: LTCUSDT (без / и :USDT)
    #             symbol_clean = symbol.replace('/', '').replace(':USDT', '')
    #
    #             params = {
    #                 'symbol': symbol_clean,
    #                 'category': 'linear'  # Для USDT-M фьючерсов
    #             }
    #
    #             if stop_loss:
    #                 params['stopLoss'] = str(stop_loss)
    #             if take_profit:
    #                 params['takeProfit'] = str(take_profit)
    #
    #             if stop_loss or take_profit:
    #                 # Используем private API для установки TP/SL
    #                 # В CCXT это может быть через set_position_mode или прямой API вызов
    #                 try:
    #                     # Пробуем через CCXT метод если есть
    #                     if hasattr(self.client, 'set_position_tp_sl'):
    #                         result = await self.client.set_position_tp_sl(symbol, stop_loss, take_profit)
    #                     else:
    #                         # Используем прямой API вызов
    #                         result = await self.client.private_post_v5_position_trading_stop(params)
    #                     logger.info(f"Установлен TP/SL для позиции {symbol}: SL={stop_loss}, TP={take_profit}")
    #                     return result
    #                 except AttributeError:
    #                     # Если метод не существует, используем прямой вызов
    #                     result = await self.client.private_post_v5_position_trading_stop(params)
    #                     logger.info(f"Установлен TP/SL для позиции {symbol}: SL={stop_loss}, TP={take_profit}")
    #                     return result
    #         else:
    #             logger.warning(f"Установка TP/SL на позицию не поддерживается для {self.exchange_name}")
    #         return None
    #     except Exception as e:
    #         logger.error(f"Ошибка при установке TP/SL на позицию: {e}")
    #         # Не поднимаем исключение, чтобы не блокировать выполнение
    #         return None
    
    async def close(self):
        """Закрытие соединения"""
        await self.client.close()
        logger.info(f"Соединение с {self.exchange_name} закрыто")

