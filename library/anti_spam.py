"""
Middleware для защиты от спама.
Ограничивает частоту сообщений от пользователя (1/сек).
"""
import time
import logging
from typing import Dict, Any, Awaitable
from collections import defaultdict

from aiogram import BaseMiddleware
from aiogram.types import Message

logger = logging.getLogger(__name__)

class AntiSpamMiddleware(BaseMiddleware):
    """Антиспам: лимит 1 сообщение в секунду на пользователя."""
    
    def __init__(self, rate_limit: float = 1.0):
        self.rate_limit = rate_limit
        self.user_times: Dict[int, float] = defaultdict(float)
    
    async def __call__(
        self,
        handler,
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        
        now = time.time()
        last_time = self.user_times[user_id]
        
        if now - last_time < self.rate_limit:
            logger.warning(f"Спам от {user_id}: слишком частые сообщения")
            await event.answer("⏳ Подождите секунду перед следующим сообщением!")
            return
        
        self.user_times[user_id] = now
        
        # Очистка старых записей (каждые 100 сообщений)
        if len(self.user_times) > 100:
            self.user_times.clear()
        
        return await handler(event, data)
