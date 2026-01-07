from fastapi import HTTPException, Query
from app.config.settings import settings
from app.utils.logger import logger


def validate_webhook_token(token: str = Query(...)) -> bool:
    """
    Валидация токена из query параметра
    
    Args:
        token: токен из query параметра ?token=...
    
    Returns:
        True если токен валиден
    
    Raises:
        HTTPException если токен невалиден
    """
    if token != settings.webhook_secret_token:
        logger.warning(f"Невалидный токен вебхука: {token}")
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return True

