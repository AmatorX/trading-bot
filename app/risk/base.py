class BaseRiskStrategy:
    """
    Базовый интерфейс риск-стратегии.
    """

    async def calculate(
        self,
        client,
        symbol: str,
        entry_price: float,
        side: str,
    ):
        raise NotImplementedError
