from fastapi import HTTPException
from app.models.webhook import TradingViewWebhook
from app.models.trade import TradeSignal
from app.parser.tradingview import TradingViewParser
from app.exchange.order_manager import OrderManager
from app.exchange.factory import ExchangeFactory
from app.models.order import OrderRequest
from app.utils.risk_manager import RiskManager
from app.config.settings import settings
from app.utils.logger import logger


class WebhookHandler:
    """Обработчик вебхуков от TradingView"""
    
    def __init__(self):
        self.parser = TradingViewParser()
        self.order_manager = OrderManager()
    
    async def process_webhook(self, webhook: TradingViewWebhook) -> dict:
        """
        Обработка вебхука от TradingView
        
        Args:
            webhook: данные вебхука
        
        Returns:
            dict с результатом обработки
        """
        import time
        webhook_start_time = time.time()
        try:
            # Извлекаем текст сообщения
            message = webhook.get_message_text()
            if not message:
                raise ValueError("Пустое сообщение в вебхуке")
            
            logger.info(f"Получен вебхук: {message}")
            
            # Парсим алерт
            trade_signal = self.parser.parse_alert(message)
            
            # Проверяем риски
            is_valid, error_msg = RiskManager.check_risk_limits(
                size=trade_signal.size or settings.size_position,
                leverage=trade_signal.leverage or settings.default_leverage,
                price=trade_signal.entry_price
            )
            
            if not is_valid:
                raise ValueError(f"Проверка рисков не пройдена: {error_msg}")
            
            # Определяем биржу
            exchange = trade_signal.exchange or settings.exchange
            
            # Рассчитываем стоп-лосс и тейк-профит на основе ATR
            stop_loss, take_profit = await self.order_manager.calculate_stop_loss_take_profit(
                exchange_name=exchange,
                symbol=trade_signal.symbol,
                entry_price=trade_signal.entry_price,
                direction=trade_signal.direction,
                contract_type=settings.contract_type
            )
            
            # Определяем сторону ордера
            side = "buy" if trade_signal.direction == "LONG" else "sell"
            
            # Создаем запрос на ордер
            order_request = OrderRequest(
                symbol=trade_signal.symbol,
                side=side,
                amount=trade_signal.size or settings.size_position,
                leverage=trade_signal.leverage or settings.default_leverage,
                stop_loss=stop_loss,
                take_profit=take_profit,
                contract_type=settings.contract_type,
                exchange=exchange,
                entry_price=trade_signal.entry_price  # Цена из алерта (для limit ордеров)
            )
            
            # Выполняем сделку
            order_response = await self.order_manager.execute_trade(order_request)
            
            if order_response.success:
                total_time = time.time() - webhook_start_time
                logger.info(
                    f"Сделка успешно выполнена: {trade_signal.symbol} "
                    f"{trade_signal.direction} @ {trade_signal.entry_price} "
                    f"(общее время обработки: {total_time:.2f}с)"
                )
                return {
                    "success": True,
                    "message": "Сделка успешно выполнена",
                    "order_id": order_response.order_id,
                    "stop_loss": round(stop_loss, 4),
                    "take_profit": round(take_profit, 4),
                    "symbol": trade_signal.symbol,
                    "direction": trade_signal.direction,
                    "entry_price": trade_signal.entry_price,
                    "execution_time_seconds": round(total_time, 2)
                }
            else:
                raise Exception(order_response.error or "Неизвестная ошибка при выполнении сделки")
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Ошибка при обработке вебхука: {error_msg}")
            # Более понятные сообщения об ошибках
            if "apiKey" in error_msg.lower() or "credential" in error_msg.lower():
                error_msg = "Не настроены API ключи для биржи. Проверьте файл .env"
            elif "not enough" in error_msg.lower() or "insufficient" in error_msg.lower() or "110007" in error_msg:
                error_msg = "Недостаточно баланса для открытия позиции. Проверьте баланс на бирже."
            elif "retCode" in error_msg or "retMsg" in error_msg:
                # Парсим ошибку от Bybit
                import json
                try:
                    if "{" in error_msg:
                        error_json = json.loads(error_msg.split("{")[1].split("}")[0] + "}")
                        if "retMsg" in error_json:
                            error_msg = f"Ошибка биржи: {error_json['retMsg']}"
                except:
                    pass
            raise HTTPException(status_code=400, detail=error_msg)
    
    async def cleanup(self):
        """Очистка ресурсов"""
        await self.order_manager.close_all_connections()

