# import re
# from typing import Optional
# from app.models.trade import TradeSignal
# from app.config.settings import settings
# from app.utils.logger import logger
#
#
# class TradingViewParser:
#     """Парсер алертов от TradingView"""
#
#     # Поддерживаемые биржи
#     EXCHANGES = ["binance", "okx", "bybit", "bitget"]
#
#     @staticmethod
#     def parse_alert(message: str) -> TradeSignal:
#         """
#         Парсинг алерта от TradingView
#
#         Формат: SYMBOL Crossing Up/Down PRICE [size=SIZE] [lev=LEVERAGE] [EXCHANGE]
#
#         Примеры:
#         - LTCUSDT Crossing Down 76.47
#         - LTCUSDT Crossing Up 76.47 size=100
#         - LTCUSDT Crossing Up 76.47 size=100 lev=35
#         - LTCUSDT Crossing Down 76.49 Bybit
#         - LTCUSDT Crossing Up 76.47 size=100 lev=35 Binance
#         """
#         message = message.strip()
#         logger.info(f"Парсинг алерта: {message}")
#
#         # Определяем направление
#         if "Crossing Up" in message:
#             direction = "LONG"
#             pattern = r"(\w+)\s+Crossing Up\s+([\d.]+)"
#         elif "Crossing Down" in message:
#             direction = "SHORT"
#             pattern = r"(\w+)\s+Crossing Down\s+([\d.]+)"
#         else:
#             raise ValueError(f"Не удалось определить направление в сообщении: {message}")
#
#         # Извлекаем символ и цену
#         match = re.search(pattern, message)
#         if not match:
#             raise ValueError(f"Не удалось распарсить символ и цену из: {message}")
#
#         symbol = match.group(1)
#         entry_price = float(match.group(2))
#
#         # Извлекаем размер позиции (size=100)
#         size = None
#         size_match = re.search(r"size=([\d.]+)", message, re.IGNORECASE)
#         if size_match:
#             size = float(size_match.group(1))
#         else:
#             size = settings.size_position
#
#         # Извлекаем кредитное плечо (lev=35)
#         leverage = None
#         lev_match = re.search(r"lev=(\d+)", message, re.IGNORECASE)
#         if lev_match:
#             leverage = int(lev_match.group(1))
#         else:
#             leverage = settings.default_leverage
#
#         # Извлекаем биржу (Bybit, Binance, OKX, Bitget)
#         exchange = None
#         message_lower = message.lower()
#         for exch in TradingViewParser.EXCHANGES:
#             if exch in message_lower:
#                 exchange = exch
#                 break
#
#         if not exchange:
#             exchange = settings.exchange
#
#         logger.info(
#             f"Распарсено: symbol={symbol}, direction={direction}, "
#             f"price={entry_price}, size={size}, leverage={leverage}, exchange={exchange}"
#         )
#
#         return TradeSignal(
#             symbol=symbol,
#             direction=direction,
#             entry_price=entry_price,
#             size=size,
#             leverage=leverage,
#             exchange=exchange
#         )
#
import re
from app.models.trade import TradeSignal
from app.config.settings import settings
from app.utils.logger import logger


class TradingViewParser:
    """Парсер алертов от TradingView"""

    EXCHANGES = ["binance", "okx", "bybit", "bitget"]

    @staticmethod
    def parse_alert(message: str) -> TradeSignal:
        """
        Формат: SYMBOL Crossing Up/Down PRICE [size=SIZE] [lev=LEVERAGE] [EXCHANGE]

        Примеры:
        - LTCUSDT Crossing Down 76.47
        - BTCUSDT Crossing Down 90,350.00
        - ONTUSDT.P Crossing Up 0.07624
        """
        message = message.strip()
        logger.info(f"Парсинг алерта: {message}")

        # ---- Определяем направление ----
        if "Crossing Up" in message:
            direction = "LONG"
            pattern = r"([\w\.]+)\s+Crossing Up\s+([\d.,]+)"
        elif "Crossing Down" in message:
            direction = "SHORT"
            pattern = r"([\w\.]+)\s+Crossing Down\s+([\d.,]+)"
        else:
            raise ValueError(f"Не удалось определить направление в сообщении: {message}")

        # ---- Извлекаем символ и цену ----
        match = re.search(pattern, message)
        if not match:
            raise ValueError(f"Не удалось распарсить символ и цену из: {message}")

        symbol_raw = match.group(1)

        # Убираем TradingView ".P" суффикс фьючерсов Bybit
        symbol = symbol_raw.replace(".P", "").replace(".p", "")

        # ---- Цена ----
        raw_price = match.group(2)
        entry_price = float(raw_price.replace(",", ""))

        # ---- Размер позиции ----
        size_match = re.search(r"size=([\d.]+)", message, re.IGNORECASE)
        size = float(size_match.group(1)) if size_match else settings.size_position

        # ---- Плечо ----
        lev_match = re.search(r"lev=(\d+)", message, re.IGNORECASE)
        leverage = int(lev_match.group(1)) if lev_match else settings.default_leverage

        # ---- Биржа ----
        message_lower = message.lower()
        exchange = next((ex for ex in TradingViewParser.EXCHANGES if ex in message_lower), None)
        if not exchange:
            exchange = settings.exchange

        logger.info(
            f"Распарсено: symbol={symbol}, direction={direction}, "
            f"price={entry_price}, size={size}, leverage={leverage}, exchange={exchange}"
        )

        return TradeSignal(
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            size=size,
            leverage=leverage,
            exchange=exchange
        )
