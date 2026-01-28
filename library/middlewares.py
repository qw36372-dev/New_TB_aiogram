"""
Middlewares: AntiSpam (flood protect), ErrorHandler.
Для dp.message.middleware(AntiSpamMiddleware()).
"""
import logging
import time
from typing import Dict, Any
from collections import defaultdict, deque
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

logger = logging.getLogger(__name__)

class AntiSpamMiddleware(BaseMiddleware):
    """Rate limit: max 5 msg/sec per user."""
    
    def __init__(self, max_requests: int = 5, window: int = 1):
        self.max_requests = max_requests
        self.window = window
        self.user_requests: Dict[int, deque[float]] = defaultdict(deque)
    
    async def __call__(
        self, 
        handler, 
        event: Message | CallbackQuery, 
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        now = time.time()
        
        # Cleanup old
        req_queue = self.user_requests[user_id]
        req_queue[:] = [t for t in req_queue if now - t < self.window]
        
        if len(req_queue) >= self.max_requests:
            await event.answer("⏳ Не спамь! Подожди секунду.")
            return
        
        req_queue.append(now)
        return await handler(event, data)

class ErrorHandlerMiddleware(BaseMiddleware):
    """Catch all errors, log, answer."""
    
    async def __call__(
        self, 
        handler, 
        event: Message | CallbackQuery, 
        data: Dict[str, Any]
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as e:
            logger.error(f"Handler error {event.from_user.id}: {e}", exc_info=True)
            if isinstance(event, CallbackQuery):
                try:
                    await event.answer("❌ Ошибка сервера")
                except:
                    pass
            else:
                await event.answer("❌ Ошибка. Попробуй /start")
