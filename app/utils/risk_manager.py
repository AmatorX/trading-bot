from app.config.settings import settings
from app.utils.logger import logger


class RiskManager:
    """Управление рисками перед выставлением ордеров"""
    
    @staticmethod
    def validate_position_size(size: float) -> bool:
        """Проверка размера позиции на соответствие лимитам"""
        if size <= 0:
            logger.warning(f"Размер позиции должен быть больше 0: {size}")
            return False
        
        if size > settings.max_position_size:
            logger.warning(
                f"Размер позиции {size} превышает максимальный лимит {settings.max_position_size}"
            )
            return False
        
        return True
    
    @staticmethod
    def validate_leverage(leverage: int) -> bool:
        """Проверка кредитного плеча"""
        if leverage < 1 or leverage > 125:
            logger.warning(f"Некорректное значение плеча: {leverage}")
            return False
        
        return True
    
    @staticmethod
    def validate_price(price: float) -> bool:
        """Проверка цены"""
        if price <= 0:
            logger.warning(f"Цена должна быть больше 0: {price}")
            return False
        
        return True
    
    @staticmethod
    def check_risk_limits(size: float, leverage: int, price: float) -> tuple[bool, str]:
        """Комплексная проверка всех лимитов"""
        if not RiskManager.validate_price(price):
            return False, "Некорректная цена"
        
        if not RiskManager.validate_position_size(size):
            return False, f"Размер позиции превышает лимит {settings.max_position_size}"
        
        if not RiskManager.validate_leverage(leverage):
            return False, "Некорректное значение кредитного плеча"
        
        return True, "OK"

