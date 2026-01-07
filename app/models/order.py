from pydantic import BaseModel
from typing import Optional, Literal


class OrderRequest(BaseModel):
    """Запрос на создание ордера"""
    symbol: str
    side: Literal["buy", "sell"]
    amount: float
    leverage: int
    stop_loss: float
    take_profit: float
    contract_type: Literal["USDT-M", "COIN-M"]
    exchange: str
    entry_price: Optional[float] = None  # Цена входа (для limit ордеров)


class OrderResponse(BaseModel):
    """Ответ после создания ордера"""
    success: bool
    order_id: Optional[str] = None
    position_id: Optional[str] = None
    stop_loss_order_id: Optional[str] = None
    take_profit_order_id: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None

