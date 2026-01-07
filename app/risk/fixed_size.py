from app.risk.base import BaseRiskStrategy
from app.risk.models import RiskResult
from app.utils.indicators import get_atr_for_symbol
from app.config.settings import settings


class FixedSizeRisk(BaseRiskStrategy):
    """
    Фиксированный объём позиции.
    Риск плавающий (SL / TP от ATR).
    """

    async def calculate(self, client, symbol, entry_price, side) -> RiskResult:
        atr = await get_atr_for_symbol(client, symbol)

        amount = settings.size_position / entry_price

        stop_distance = atr * settings.stop_loss_rate
        take_distance = atr * settings.take_profit_rate

        if side == "buy":
            stop = entry_price - stop_distance
            take = entry_price + take_distance
        else:
            stop = entry_price + stop_distance
            take = entry_price - take_distance

        return RiskResult(amount, stop, take)

