from typing import Optional
from app.exchange.client import ExchangeClient
from app.config.settings import settings
from app.utils.logger import logger


class ExchangeFactory:
    """Фабрика для создания клиентов бирж"""
    
    @staticmethod
    def create_client(exchange_name: str) -> ExchangeClient:
        """
        Создание клиента для биржи
        
        Args:
            exchange_name: название биржи (binance, okx, bybit, bitget)
        
        Returns:
            ExchangeClient
        """
        exchange_name = exchange_name.lower()
        
        if exchange_name == "binance":
            return ExchangeClient(
                exchange_name="binance",
                api_key=settings.binance_api_key,
                api_secret=settings.binance_api_secret,
                sandbox=settings.binance_sandbox
            )
        elif exchange_name == "okx":
            return ExchangeClient(
                exchange_name="okx",
                api_key=settings.okx_api_key,
                api_secret=settings.okx_api_secret,
                passphrase=settings.okx_passphrase,
                sandbox=settings.okx_sandbox
            )
        elif exchange_name == "bybit":
            if not settings.bybit_api_key or not settings.bybit_api_secret:
                raise ValueError(
                    "BYBIT_API_KEY и BYBIT_API_SECRET должны быть указаны в .env файле"
                )
            return ExchangeClient(
                exchange_name="bybit",
                api_key=settings.bybit_api_key,
                api_secret=settings.bybit_api_secret,
                sandbox=settings.bybit_sandbox
            )
        elif exchange_name == "bitget":
            return ExchangeClient(
                exchange_name="bitget",
                api_key=settings.bitget_api_key,
                api_secret=settings.bitget_api_secret,
                passphrase=settings.bitget_passphrase,
                sandbox=settings.bitget_sandbox
            )
        else:
            raise ValueError(f"Неподдерживаемая биржа: {exchange_name}")
    
    @staticmethod
    def get_symbol_format(exchange_name: str, symbol: str, contract_type: str) -> str:
        """
        Преобразование символа в формат биржи
        
        Args:
            exchange_name: название биржи
            symbol: символ (например, LTCUSDT)
            contract_type: тип контракта (USDT-M или COIN-M)
        
        Returns:
            Форматированный символ для биржи
        """
        exchange_name = exchange_name.lower()
        
        # Для фьючерсов обычно формат: BASE/QUOTE:QUOTE или BASE/USDT:USDT
        if "USDT" in symbol:
            base = symbol.replace("USDT", "")
            if contract_type == "USDT-M":
                # USDT-M фьючерсы
                if exchange_name == "binance":
                    return f"{base}/USDT:USDT"
                elif exchange_name == "okx":
                    return f"{base}/USDT:USDT"
                elif exchange_name == "bybit":
                    return f"{base}/USDT:USDT"
                elif exchange_name == "bitget":
                    return f"{base}/USDT:USDT"
            else:
                # COIN-M фьючерсы
                if exchange_name == "binance":
                    return f"{base}/USD:{base}"
                elif exchange_name == "okx":
                    return f"{base}/USD:{base}"
                elif exchange_name == "bybit":
                    return f"{base}/USD:{base}"
                elif exchange_name == "bitget":
                    return f"{base}/USD:{base}"
        
        # Если не удалось распознать, возвращаем как есть
        logger.warning(f"Не удалось определить формат символа для {symbol}, возвращаем как есть")
        return symbol

