from pydantic import BaseModel
from typing import Optional


class TradingViewWebhook(BaseModel):
    """Модель входящего вебхука от TradingView"""
    message: Optional[str] = None
    text: Optional[str] = None
    symbol: Optional[str] = None
    action: Optional[str] = None
    
    def get_message_text(self) -> str:
        """Извлекает текст сообщения из вебхука"""
        return self.message or self.text or ""

