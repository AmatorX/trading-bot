from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.webhook.handler import WebhookHandler
from app.webhook.validator import validate_webhook_token
from app.models.webhook import TradingViewWebhook
from app.exchange.factory import ExchangeFactory
from app.config.settings import settings
from app.utils.logger import logger
from app.api.signal import router as signal_router


# Глобальный обработчик вебхуков
webhook_handler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    global webhook_handler
    # Startup
    logger.info("Запуск приложения...")
    webhook_handler = WebhookHandler()
    yield
    # Shutdown
    logger.info("Остановка приложения...")
    if webhook_handler:
        await webhook_handler.cleanup()


app = FastAPI(
    title="Trading Bot",
    description="Торговый бот для фьючерсной торговли на биржах",
    version="1.0.0",
    lifespan=lifespan
)
app.include_router(signal_router)


@app.get("/")
async def root():
    """Корневой endpoint"""
    return {"message": "Trading Bot API", "status": "running"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/balance")
async def get_balance(
    exchange: str = Query(None, description="Название биржи (по умолчанию из .env)"),
    token: str = Query(..., description="Секретный токен для доступа")
):
    """
    Получение баланса на бирже
    
    Args:
        exchange: название биржи (binance, okx, bybit, bitget). Если не указано, используется из .env
        token: секретный токен для доступа
    
    Returns:
        JSON с балансом
    """
    # Валидация токена
    validate_webhook_token(token)
    
    # Определяем биржу
    exchange_name = exchange.lower() if exchange else settings.exchange
    
    try:
        # Создаем клиент
        client = ExchangeFactory.create_client(exchange_name)
        await client.load_markets()
        
        # Получаем баланс
        balance = await client.get_balance()
        
        # Форматируем ответ
        result = {
            "exchange": exchange_name,
            "balance": {}
        }
        
        # Извлекаем доступные балансы
        if "USDT" in balance:
            result["balance"]["USDT"] = {
                "free": balance["USDT"].get("free", 0),
                "used": balance["USDT"].get("used", 0),
                "total": balance["USDT"].get("total", 0)
            }
        
        # Добавляем другие валюты если есть
        for currency, info in balance.items():
            if currency not in ["info", "free", "used", "total"] and isinstance(info, dict):
                if info.get("total", 0) > 0 or info.get("free", 0) > 0:
                    result["balance"][currency] = {
                        "free": info.get("free", 0),
                        "used": info.get("used", 0),
                        "total": info.get("total", 0)
                    }
        
        await client.close()
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Ошибка при получении баланса: {e}")
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": str(e)}
        )


@app.post("/webhook/tradingview")
async def tradingview_webhook(
    request: Request,
    token: str = Query(..., description="Секретный токен для вебхука")
):
    """
    Endpoint для приема вебхуков от TradingView
    
    Args:
        request: HTTP запрос
        token: секретный токен из query параметра
    
    Returns:
        JSON ответ с результатом обработки
    """
    # Валидация токена
    validate_webhook_token(token)
    
    # Получаем тело запроса
    try:
        body = await request.json()
        webhook = TradingViewWebhook(**body)
    except Exception as e:
        # Если не JSON, пробуем получить как текст
        try:
            body_text = await request.body()
            webhook = TradingViewWebhook(message=body_text.decode('utf-8'))
        except Exception as e2:
            logger.error(f"Ошибка при парсинге тела запроса: {e2}")
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Не удалось распарсить тело запроса"}
            )
    
    # Обрабатываем вебхук
    try:
        result = await webhook_handler.process_webhook(webhook)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Ошибка при обработке вебхука: {e}")
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": str(e)}
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

