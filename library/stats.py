"""
Управление статистикой прохождений (SQLite).
Хранит успешные попытки по user_id.
"""
import aiosqlite
import asyncio
from typing import List, Dict, Any
from pathlib import Path

from config.settings import settings
from .models import TestResult

class StatsManager:
    """Менеджер статистики."""
    
    DB_PATH = settings.data_dir / "stats.db"
    
    def __init__(self):
        self.db_path = self.DB_PATH
    
    async def init_db(self):
        """Инициализация БД."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    specialization TEXT,
                    difficulty TEXT,
                    grade TEXT,
                    percentage REAL,
                    date TEXT,
                    result_json TEXT
                )
            """)
            await db.commit()
    
    async def save_result(self, user_id: int, result: TestResult):
        """Сохраняет успешный результат."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO stats (user_id, specialization, difficulty, grade, percentage, date, result_json)
                VALUES (?, ?, ?, ?, ?, datetime('now'), ?)
            """, (
                user_id,
                result.user_data.specialization,
                result.user_data.difficulty.value,
                result.grade,
                result.percentage,
                result.model_dump_json()
            ))
            await db.commit()
    
    async def get_user_stats(self, user_id: int) -> List[Dict[str, Any]]:
        """Возвращает статистику пользователя."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT specialization, difficulty, grade, percentage, date
                FROM stats WHERE user_id = ? ORDER BY date DESC
            """, (user_id,)) as cursor:
                return await cursor.fetchall()

# Глобальный экземпляр
stats_manager = StatsManager()
