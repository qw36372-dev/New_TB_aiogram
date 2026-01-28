"""
Управление таймерами теста по уровню сложности.
Persistent: total_seconds от start_time, нет drift.
remaining_time() → "MM:SS" для _show_question.
"""
import asyncio
import logging
from typing import Optional, Callable
from datetime import timedelta

from config.settings import settings
from .models import Difficulty

logger = logging.getLogger(__name__)

class TestTimer:
    """Таймер теста."""
    
    def __init__(self, total_minutes: int):
        self.total_seconds = total_minutes * 60
        self.start_time: Optional[float] = None
        self.timeout_callback: Optional[Callable] = None
        self.task: Optional[asyncio.Task] = None
    
    async def start(self, timeout_callback: Optional[Callable] = None) -> None:
        """Запуск таймера + task для timeout."""
        self.timeout_callback = timeout_callback
        self.start_time = asyncio.get_event_loop().time()
        
        async def countdown():
            while self.remaining_seconds() > 0:
                await asyncio.sleep(1)
            await self._on_timeout()
        
        self.task = asyncio.create_task(countdown())
        logger.info(f"Timer start: {self.total_seconds}s")
    
    def stop(self) -> None:
        """Graceful stop."""
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                asyncio.get_event_loop().run_until_complete(self.task)
            except asyncio.CancelledError:
                pass
        self.start_time = None
        logger.info("Timer stopped")
    
    def remaining_seconds(self) -> int:
        """Остаток секунд."""
        if not self.start_time:
            return self.total_seconds
        elapsed = asyncio.get_event_loop().time() - self.start_time
        return max(0, int(self.total_seconds - elapsed))
    
    def remaining_time(self) -> str:
        """'MM:SS' для UI."""
        secs = self.remaining_seconds()
        mins, s = divmod(secs, 60)
        return f"{mins:02d}:{s:02d}"
    
    async def _on_timeout(self) -> None:
        """Timeout: auto finish."""
        logger.warning("Test timeout!")
        if self.timeout_callback:
            await self.timeout_callback()

# Factory
def create_timer(difficulty: Difficulty) -> TestTimer:
    """Создать по сложности."""
    minutes = settings.difficulty_times.get(difficulty.value, 30)
    return TestTimer(minutes)
