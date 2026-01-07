from pydantic import BaseModel
from typing import Optional, Literal


class TradeSignal(BaseModel):
    """Распарсенный торговый сигнал из алерта TradingView"""
    symbol: str
    direction: Literal["LONG", "SHORT"]
    entry_price: float
    size: Optional[float] = None
    leverage: Optional[int] = None
    exchange: Optional[Literal["binance", "okx", "bybit", "bitget"]] = None

