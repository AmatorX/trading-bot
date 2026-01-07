from typing import NamedTuple


class RiskResult(NamedTuple):
    """
    Результат расчёта риска.
    """
    amount: float
    stop_loss: float
    take_profit: float
