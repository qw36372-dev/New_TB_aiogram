"""
Конфигурация бота: пути, тайминги, токен из окружения.
Production-ready: Pydantic v2, 4 уровня сложности (русские ключи).
"""
import os
from pathlib import Path
from typing import Dict

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Настройки бота."""
    api_token: str = os.getenv("API_TOKEN", "")  # ✅ Твой (Bothost.ru: API_TOKEN)
    
    # Пути к файлам и папкам
    base_dir: Path = Path(__file__).parent.parent  # ✅ Относительные пути (лучше для Bothost)
    questions_dir: Path = base_dir / "questions"
    assets_dir: Path = base_dir / "assets"
    data_dir: Path = base_dir / "data"
    logs_dir: Path = base_dir / "logs"
    certs_dir: Path = data_dir / "certificates"
    
    # Тайминги уровней сложности (в минутах) — 4 уровня ✅
    difficulty_times: Dict[str, int] = {
        "резерв": 35,
        "базовый": 25,
        "стандартный": 20,
        "продвинутый": 20
    }
    
    # Количество вопросов по уровням — ТВОЙ лучше (30/40/50) ✅
    difficulty_questions: Dict[str, int] = {
        "резерв": 20,
        "базовый": 30,
        "стандартный": 40,
        "продвинутый": 50
    }
    
    # Пороги оценок (процент правильных) — ТВОЙ ✅
    grades: Dict[str, float] = {
        "неудовлетворительно": 59.0,
        "удовлетворительно": 69.0,
        "хорошо": 79.0,
        "отлично": 100.0
    }
    
    # Специализации (11 штук) — ТВОЙ ✅
    specializations: list[str] = [
        "oupds", "ispolniteli", "aliment", "doznanie", "rozyisk",
        "prof", "oko", "informatika", "kadry", "bezopasnost", "upravlenie"
    ]
    
    # Время показа правильных ответов (секунды) — ТВОЙ ✅
    answers_show_time: int = 60
    
    # Логирование (нужно для library.py logging)
    log_level: str = "INFO"  # ✅ Добавлено для test_bot_main.py
    
    model_config = {"case_sensitive": False}

# Создание служебных папок
settings = Settings()
for path in [settings.data_dir, settings.logs_dir, settings.certs_dir]:
    path.mkdir(parents=True, exist_ok=True)
