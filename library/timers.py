"""
Управление таймерами теста (по уровню сложности).
Таймер идёт постоянно с момента старта теста.
"""
import asyncio
from typing import Optional, Callable
from datetime import timedelta

from config.settings import settings

from .enum import Difficulty

class TestTimer:
    """Таймер для одного теста."""
    
    def __init__(self, bot, chat_id: int, user_id: int, difficulty: Difficulty):
        self.bot = bot
        self.chat_id = chat_id
        self.user_id = user_id
        self.difficulty = difficulty
        self.minutes = settings.difficulty_times[difficulty.value]
        self.total_seconds = self.minutes * 60
        self.start_time = None
        self.task: Optional[asyncio.Task] = None
        self.is_active = False
        self.timeout_callback: Optional[Callable] = None
    
    async def start(self, timeout_callback: Callable):
        """Запуск таймера."""
        self.timeout_callback = timeout_callback
        self.start_time = asyncio.get_event_loop().time()
        self.is_active = True
        self.task = asyncio.create_task(self._countdown())
    
    async def _countdown(self):
        """Основной цикл таймера."""
        for remaining in range(self.total_seconds, 0, -1):
            await asyncio.sleep(1)
            if not self.is_active:
                return
        
        # Таймаут!
        self.is_active = False
        if self.timeout_callback:
            await self.timeout_callback()
    
    async def stop(self) -> str:
        """Остановка и возврат затраченного времени."""
        if self.is_active:
            self.is_active = False
            if self.task:
                self.task.cancel()
                try:
                    await self.task
                except asyncio.CancelledError:
                    pass
        
        if self.start_time:
            elapsed = asyncio.get_event_loop().time() - self.start_time
            elapsed_min = int(elapsed // 60)
            elapsed_sec = int(elapsed % 60)
            return f"{elapsed_min}:{elapsed_sec:02d}"
        return "0:00"
    
    def remaining_time(self) -> str:
        """Оставшееся время (для UI)."""
        if not self.start_time:
            return f"{self.minutes}:00"
        elapsed = asyncio.get_event_loop().time() - self.start_time
        remaining = max(0, self.total_seconds - elapsed)
        min_ = int(remaining // 60)
        sec = int(remaining % 60)
        return f"{min_}:{sec:02d}"
    
    def remaining_seconds(self) -> int:
        """Оставшиеся секунды (int для расчётов)."""
        if not self.start_time:
            return self.total_seconds
        elapsed = asyncio.get_event_loop().time() - self.start_time
        return max(0, int(self.total_seconds - elapsed))
