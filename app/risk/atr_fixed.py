from app.risk.base import BaseRiskStrategy
from app.risk.models import RiskResult
from app.utils.indicators import get_atr_for_symbol
from app.config.settings import settings
from app.utils.logger import logger


# class AtrFixedRisk(BaseRiskStrategy):
#     """
#     ATR + фиксированный риск в $.
#     """
#
#     async def calculate(self, client, symbol, entry_price, side) -> RiskResult:
#         atr = await get_atr_for_symbol(client, symbol)
#
#         stop_distance = atr * settings.atr_multiplier
#         risk = settings.risk_per_trade
#         rr = settings.risk_reward_ratio
#
#         amount = risk / stop_distance
#         notional = amount * entry_price
#
#         # 🔍 КЛЮЧЕВОЕ ЛОГИРОВАНИЕ
#         logger.info(
#             f"[RISK] {symbol} | "
#             f"price={entry_price:.6f} | "
#             f"ATR={atr:.6f} | "
#             f"stop={stop_distance:.6f} | "
#             f"amount={amount:.4f} | "
#             f"notional={notional:.2f} | "
#             f"min={settings.min_position_usdt} | "
#             f"max={settings.max_position_usdt}"
#         )
#
#         if notional > settings.max_position_usdt:
#             logger.warning(
#                 f"[RISK SKIP] {symbol} Position too large: {notional:.2f} > {settings.max_position_usdt}"
#             )
#             raise ValueError("Position too large")
#
#         if notional < settings.min_position_usdt:
#             logger.warning(
#                 f"[RISK SKIP] {symbol} Position too small: {notional:.2f} < {settings.min_position_usdt}"
#             )
#             raise ValueError("Position too small")
#
#         if side == "buy":
#             stop = entry_price - stop_distance
#             take = entry_price + stop_distance * rr
#         else:
#             stop = entry_price + stop_distance
#             take = entry_price - stop_distance * rr
#
#         return RiskResult(amount, stop, take)


class AtrFixedRisk(BaseRiskStrategy):
    """
    ATR + фиксированный риск в $ + ДЕНЕЖНЫЙ тейк.
    """

    async def calculate(self, client, symbol, entry_price, side) -> RiskResult:
        atr = await get_atr_for_symbol(client, symbol)

        stop_distance = atr * settings.atr_multiplier
        risk = settings.risk_per_trade
        rr = settings.risk_reward_ratio

        # 🔹 Размер позиции (гарантирует -risk USDT на стопе)
        amount = risk / stop_distance
        notional = amount * entry_price

        logger.info(
            f"[RISK] {symbol} | "
            f"price={entry_price:.6f} | "
            f"ATR={atr:.6f} | "
            f"stop={stop_distance:.6f} | "
            f"amount={amount:.4f} | "
            f"notional={notional:.2f} | "
            f"min={settings.min_position_usdt} | "
            f"max={settings.max_position_usdt}"
        )

        if notional > settings.max_position_usdt:
            raise ValueError("Position too large")

        if notional < settings.min_position_usdt:
            raise ValueError("Position too small")

        # 🔹 Деньги, которые хотим заработать
        profit_usd = risk * rr

        # 🔹 Перевод денег в расстояние цены
        take_distance = profit_usd / amount

        if side == "buy":
            stop = entry_price - stop_distance
            take = entry_price + take_distance
        else:
            stop = entry_price + stop_distance
            take = entry_price - take_distance

        return RiskResult(amount, stop, take)



