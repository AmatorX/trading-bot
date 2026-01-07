from app.exchange.client import ExchangeClient
from app.exchange.factory import ExchangeFactory
from app.models.order import OrderRequest, OrderResponse
from app.config.settings import settings
from app.utils.logger import logger
from app.risk.manager import RiskManager


class OrderManager:
    """
    Менеджер ордеров.

    Отвечает за:
    - получение клиента биржи
    - открытие позиции
    - установку TP / SL

    Вся логика риска вынесена в RiskManager.
    """

    def __init__(self):
        self.clients: dict[str, ExchangeClient] = {}

    # ------------------------------------------------------------------
    # CLIENT
    # ------------------------------------------------------------------

    async def _get_client(self, exchange_name: str) -> ExchangeClient:
        if exchange_name not in self.clients:
            client = ExchangeFactory.create_client(exchange_name)
            await client.load_markets()
            self.clients[exchange_name] = client
        return self.clients[exchange_name]

    # ------------------------------------------------------------------
    # ORCHESTRATOR
    # ------------------------------------------------------------------

    async def execute_trade(self, order_request: OrderRequest) -> OrderResponse:
        import time
        start_time = time.time()

        try:
            client = await self._get_client(order_request.exchange)
            symbol = self._format_symbol(order_request)

            self._log_trade_start(symbol, order_request)

            await self._setup_leverage(client, symbol, order_request)

            # --------------------------------------------------
            # Получаем цену для расчёта риска
            # --------------------------------------------------
            entry_price = await self._get_entry_price_for_calc(
                client, symbol, order_request
            )

            if not entry_price:
                raise ValueError("Не удалось получить цену для расчёта риска")

            # --------------------------------------------------
            # RISK MANAGEMENT (ключевая точка)
            # --------------------------------------------------
            risk_strategy = RiskManager.get_strategy()

            risk = await risk_strategy.calculate(
                client=client,
                symbol=symbol,
                entry_price=entry_price,
                side=order_request.side,
            )

            order_amount = risk.amount
            order_request.stop_loss = risk.stop_loss
            order_request.take_profit = risk.take_profit

            # --------------------------------------------------
            # Открытие позиции
            # --------------------------------------------------
            order_params = self._prepare_order_params(order_request)

            entry_order, actual_entry_price = await self._open_position(
                client=client,
                symbol=symbol,
                order_request=order_request,
                amount=order_amount,
                params=order_params,
            )

            # --------------------------------------------------
            # Установка TP / SL
            # --------------------------------------------------
            stop_loss_order, take_profit_order = await self._setup_tp_sl(
                client=client,
                symbol=symbol,
                order_request=order_request,
                amount=order_amount,
                entry_order=entry_order,
            )

            execution_time = time.time() - start_time
            logger.info(f"⏱️ Сделка выполнена за {execution_time:.2f} сек")

            return OrderResponse(
                success=True,
                order_id=entry_order.get("id"),
                stop_loss_order_id=stop_loss_order.get("id") if stop_loss_order else None,
                take_profit_order_id=take_profit_order.get("id") if take_profit_order else None,
                message=f"Позиция открыта (время: {execution_time:.2f}с)",
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Ошибка при выполнении сделки: {e} ({execution_time:.2f}с)")
            return OrderResponse(success=False, error=str(e))

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def _format_symbol(self, order_request: OrderRequest) -> str:
        return ExchangeFactory.get_symbol_format(
            order_request.exchange,
            order_request.symbol,
            order_request.contract_type,
        )

    def _log_trade_start(self, symbol: str, order_request: OrderRequest) -> None:
        logger.info(
            f"Сделка: {symbol} | {order_request.side} | "
            f"mode={settings.risk_mode} | leverage={order_request.leverage}"
        )

    async def _setup_leverage(
        self, client: ExchangeClient, symbol: str, order_request: OrderRequest
    ) -> None:
        try:
            market = client.client.market(symbol)
            leverage = order_request.leverage
            max_leverage = market.get("limits", {}).get("leverage", {}).get("max")

            if max_leverage and leverage > max_leverage:
                leverage = max_leverage
                logger.warning(
                    f"Плечо ограничено {max_leverage}x для {symbol}"
                )

            await client.set_leverage(symbol, leverage)

        except Exception as e:
            logger.error(f"Ошибка установки плеча для {symbol}: {e}")

    def _prepare_order_params(self, order_request: OrderRequest) -> dict:
        params = {}

        if order_request.exchange == "bybit":
            params["positionIdx"] = 1 if order_request.side.lower() == "buy" else 2

        return params

    async def _get_entry_price_for_calc(
        self,
        client: ExchangeClient,
        symbol: str,
        order_request: OrderRequest,
    ) -> float | None:
        if order_request.entry_price:
            return order_request.entry_price

        try:
            ticker = await client.client.fetch_ticker(symbol)
            return ticker.get("last")
        except Exception as e:
            logger.warning(f"Не удалось получить цену {symbol}: {e}")
            return None


    async def _open_position(
        self,
        client: ExchangeClient,
        symbol: str,
        order_request: OrderRequest,
        amount: float,
        params: dict,
    ) -> tuple[dict, float | None]:
        """
        Открывает позицию (market или limit).

        Args:
            client (ExchangeClient): Клиент биржи.
            symbol (str): Торговый символ.
            order_request (OrderRequest): Запрос на сделку.
            amount (float): Количество контрактов / монет.
            params (dict): Дополнительные параметры ордера.

        Returns:
            tuple:
                - entry_order (dict): Ордер входа.
                - actual_entry_price (float | None): Фактическая цена входа.
        """
        # -------------------------
        # LIMIT ORDER
        # -------------------------
        if settings.order_type == "limit":
            if not order_request.entry_price:
                raise ValueError("Для limit-ордера требуется entry_price")

            logger.info(
                f"Создаём LIMIT ордер: {symbol} | "
                f"{order_request.side} | "
                f"amount={amount:.6f} | "
                f"price={order_request.entry_price}"
            )

            order = await client.create_limit_order(
                symbol=symbol,
                side=order_request.side,
                amount=amount,
                price=order_request.entry_price,
                params=params or None,
            )

            return order, order_request.entry_price

        # -------------------------
        # MARKET ORDER
        # -------------------------
        logger.info(
            f"Создаём MARKET ордер: {symbol} | "
            f"{order_request.side} | "
            f"amount={amount:.6f}"
        )

        order = await client.create_market_order(
            symbol=symbol,
            side=order_request.side,
            amount=amount,
            params=params or None,
        )

        # Пытаемся получить фактическую цену входа
        actual_price = order.get("price") or order.get("average")

        if not actual_price:
            try:
                ticker = await client.client.fetch_ticker(symbol)
                actual_price = ticker.get("last")
            except Exception as e:
                logger.warning(
                    f"Не удалось получить фактическую цену входа для {symbol}: {e}"
                )
                actual_price = None

        logger.info(
            f"Позиция открыта: {symbol} | "
            f"price={actual_price}"
        )

        return order, actual_price


    # ------------------------------------------------------------------
    # TP / SL (без изменений)
    # ------------------------------------------------------------------

    async def _setup_tp_sl(
        self,
        client: ExchangeClient,
        symbol: str,
        order_request: OrderRequest,
        amount: float,
        entry_order: dict,
    ) -> tuple[dict | None, dict | None]:

        stop_loss_order = None
        take_profit_order = None

        stop_side = "sell" if order_request.side == "buy" else "buy"

        is_market = settings.order_type == "market"
        is_limit = settings.order_type == "limit"
        is_bybit = order_request.exchange == "bybit"

        if is_market and is_bybit:
            try:
                await client.set_position_tp_sl(
                    symbol=symbol,
                    stop_loss=order_request.stop_loss,
                    take_profit=order_request.take_profit,
                )
                return {"id": "position_sl"}, {"id": "position_tp"}
            except Exception:
                pass

        if is_limit and is_bybit:
            try:
                status = await client.client.fetch_order(entry_order["id"], symbol)
                if status.get("filled", 0) > 0:
                    await client.set_position_tp_sl(
                        symbol=symbol,
                        stop_loss=order_request.stop_loss,
                        take_profit=order_request.take_profit,
                    )
                    return {"id": "position_sl"}, {"id": "position_tp"}
                return None, None
            except Exception:
                pass

        try:
            stop_loss_order = await client.create_stop_loss_order(
                symbol=symbol,
                side=stop_side,
                amount=amount,
                price=order_request.stop_loss,
            )
        except Exception as e:
            logger.error(f"SL error: {e}")

        try:
            take_profit_order = await client.create_take_profit_order(
                symbol=symbol,
                side=stop_side,
                amount=amount,
                price=order_request.take_profit,
            )
        except Exception as e:
            logger.error(f"TP error: {e}")

        return stop_loss_order, take_profit_order

    # ------------------------------------------------------------------
    # CLEANUP
    # ------------------------------------------------------------------

    async def close_all_connections(self) -> None:
        for client in self.clients.values():
            await client.close()
        self.clients.clear()
