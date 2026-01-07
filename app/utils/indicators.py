from typing import List
from app.config.settings import settings
from app.utils.logger import logger


def calculate_atr(highs: List[float], lows: List[float], closes: List[float], period: int) -> float:
    """
    Расчет Average True Range (ATR)
    
    Args:
        highs: список максимальных цен
        lows: список минимальных цен
        closes: список цен закрытия
        period: период для расчета ATR
    
    Returns:
        Среднее значение ATR
    """
    if len(highs) < period + 1 or len(lows) < period + 1 or len(closes) < period + 1:
        raise ValueError(f"Недостаточно данных для расчета ATR. Требуется минимум {period + 1} свечей")
    
    true_ranges = []
    
    for i in range(1, len(highs)):
        # True Range = max(high - low, abs(high - prev_close), abs(low - prev_close))
        tr1 = highs[i] - lows[i]
        tr2 = abs(highs[i] - closes[i - 1])
        tr3 = abs(lows[i] - closes[i - 1])
        true_range = max(tr1, tr2, tr3)
        true_ranges.append(true_range)
    
    # Берем последние period значений для расчета среднего
    atr_values = true_ranges[-period:]
    atr = sum(atr_values) / len(atr_values)
    
    logger.info(f"ATR рассчитан: {atr:.4f} (период: {period})")
    return atr


async def get_atr_for_symbol(exchange_client, symbol: str) -> float:
    """
    Получение ATR для символа через биржу
    
    Args:
        exchange_client: клиент CCXT
        symbol: торговый символ (например, 'LTC/USDT:USDT')
    
    Returns:
        Среднее значение ATR
    """
    try:
        # Получаем исторические данные (OHLCV)
        # Нужно получить достаточно свечей для расчета ATR
        # Обычно нужно period + несколько дополнительных свечей
        limit = settings.atr_period + 10  # Берем с запасом
        
        ohlcv = await exchange_client.client.fetch_ohlcv(symbol, timeframe=settings.atr_timeframe, limit=limit)
        
        if len(ohlcv) < settings.atr_period + 2:  # +2: period + 1 для расчета + 1 текущая свеча
            raise ValueError(f"Недостаточно данных для расчета ATR. Получено {len(ohlcv)} свечей, требуется минимум {settings.atr_period + 2}")
        
        # Исключаем последнюю (текущую) свечу, так как она еще не закрылась
        # Используем только закрытые свечи для расчета ATR
        ohlcv_closed = ohlcv[:-1]  # Все кроме последней свечи
        
        logger.info(f"Получено {len(ohlcv)} свечей, используем {len(ohlcv_closed)} закрытых свечей для расчета ATR")
        
        # Извлекаем данные из закрытых свечей
        highs = [candle[2] for candle in ohlcv_closed]  # индекс 2 = high
        lows = [candle[3] for candle in ohlcv_closed]   # индекс 3 = low
        closes = [candle[4] for candle in ohlcv_closed] # индекс 4 = close
        
        atr = calculate_atr(highs, lows, closes, settings.atr_period)
        return atr
        
    except Exception as e:
        logger.error(f"Ошибка при расчете ATR для {symbol}: {e}")
        raise

