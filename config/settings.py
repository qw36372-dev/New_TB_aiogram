"""
Конфигурация бота: пути, тайминги, токен из окружения.
"""
import os
from pathlib import Path
from typing import Dict, Any

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Настройки бота."""
    api_token: str = os.getenv("API_TOKEN", "")
    
    # Пути к файлам и папкам
    base_dir: Path = Path(__file__).parent.parent  # Корень проекта
    questions_dir: Path = base_dir / "questions"
    assets_dir: Path = base_dir / "assets"
    data_dir: Path = base_dir / "data"
    logs_dir: Path = base_dir / "logs"
    certs_dir: Path = data_dir / "certificates"
    
    # Тайминги уровней сложности (в минутах)
    difficulty_times: Dict[str, int] = {
        "резерв": 35,
        "базовый": 25,
        "стандартный": 20,
        "продвинутый": 20
    }
    
    # Количество вопросов по уровням
    difficulty_questions: Dict[str, int] = {
        "резерв": 20,
        "базовый": 30,
        "стандартный": 40,
        "продвинутый": 50
    }
    
    # Пороги оценок (процент правильных)
    grades: Dict[str, float] = {
        "неудовлетворительно": 59.0,
        "удовлетворительно": 69.0,
        "хорошо": 79.0,
        "отлично": 100.0
    }
    
    # Специализации (11 штук)
    specializations: list[str] = [
        "oupds", "ispolniteli",  "aliment", "doznanie", "rozyisk", "prof", "oko", "informatika", "kadry", "bezopasnost", "upravlenie",
    ]
    
    # Время показа правильных ответов (секунды)
    answers_show_time: int = 60
    
    class Config:
        env_file = ".env"  # Опционально, если локально

# Создание служебных папок
settings = Settings()
for path in [settings.data_dir, settings.logs_dir, settings.certs_dir]:
    path.mkdir(parents=True, exist_ok=True)
