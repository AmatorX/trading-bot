# from fastapi import APIRouter, HTTPException, Request
# from app.utils.logger import logger
# from app.config.settings import settings
# from app.models.order import OrderRequest
# from app.exchange.order_manager import OrderManager

# router = APIRouter()
# order_manager = OrderManager()
#
# TOKEN = settings.trade_signal_token  # добавь в settings
#
#
# @router.post("/signal")
# async def receive_signal(request: Request, token: str):
#     if token != TOKEN:
#         raise HTTPException(status_code=403, detail="Forbidden")
#
#     data = await request.json()
#     logger.info(f"🔥 Получен торговый сигнал: {data}")
#
#     try:
#         symbol = data["symbol"]
#         direction = data["direction"].upper()
#
#         if direction == "LONG":
#             side = "buy"
#         elif direction == "SHORT":
#             side = "sell"
#         else:
#             raise ValueError("direction must be LONG or SHORT")
#
#         order_request = OrderRequest(
#             exchange=settings.exchange,              # bybit
#             symbol=symbol,
#             contract_type="linear",
#             side=side,
#             amount=settings.size_position,
#             leverage=settings.default_leverage,
#             entry_price=None,                        # market — цена не нужна
#             stop_loss=None,
#             take_profit=None,
#         )
#
#         result = await order_manager.execute_trade(order_request)
#
#         return result.dict()
#
#     except Exception as e:
#         logger.exception("Ошибка обработки торгового сигнала")
#         raise HTTPException(status_code=400, detail=str(e))

from fastapi import APIRouter, HTTPException, Request
from app.utils.logger import logger
from app.config.settings import settings
from app.models.order import OrderRequest
from app.exchange.order_manager import OrderManager

router = APIRouter()
order_manager = OrderManager()

TOKEN = settings.trade_signal_token


@router.post("/signal")
async def receive_signal(request: Request, token: str):
    if token != TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")

    data = await request.json()
    logger.info(f"🔥 Получен торговый сигнал: {data}")

    try:
        symbol = data["symbol"]
        direction = data["direction"].upper()

        if direction == "LONG":
            side = "buy"
        elif direction == "SHORT":
            side = "sell"
        else:
            raise ValueError("direction must be LONG or SHORT")

        order_request = OrderRequest(
            exchange=settings.exchange,                 # bybit
            symbol=symbol,
            contract_type=settings.contract_type,       # ✅ USDT-M из settings
            side=side,
            amount=settings.size_position,
            leverage=settings.default_leverage,

            entry_price=None,                           # market — будет выяснено позже
            stop_loss=0.0,                              # ⚠️ временно, пересчитается
            take_profit=0.0,
        )

        result = await order_manager.execute_trade(order_request)
        return result.model_dump()

    except Exception as e:
        logger.error("Ошибка обработки торгового сигнала", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
