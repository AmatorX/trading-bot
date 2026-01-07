from app.config.settings import settings
from app.risk.fixed_size import FixedSizeRisk
from app.risk.atr_fixed import AtrFixedRisk


class RiskManager:
    """
    Фабрика риск-стратегий.
    """

    @staticmethod
    def get_strategy():
        if settings.risk_mode == "fixed_risk_atr":
            return AtrFixedRisk()
        return FixedSizeRisk()
