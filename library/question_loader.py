"""
Загрузка вопросов из JSON файлов специализаций.
Выбор случайного подмножества по уровню сложности.
"""
import json
import logging
import random
from pathlib import Path
from typing import List

from config.settings import settings
from .models import Question, Difficulty

logger = logging.getLogger(__name__)

def load_questions_for_specialization(
    specialization: str, 
    difficulty: Difficulty, 
    seed: int = None
) -> List[Question]:
    """
    Загружает вопросы для специализации и уровня.
    
    Args:
        specialization: имя (aliment, oupds...)
        difficulty: уровень сложности
        seed: для воспроизводимости (user_id)
    
    Returns:
        Список вопросов нужного количества в случайном порядке.
    """
    if seed is not None:
        random.seed(seed)  # Разный порядок для каждого пользователя
    
    json_path = settings.questions_dir / f"{specialization}.json"
    if not json_path.exists():
        raise FileNotFoundError(f"Вопросы не найдены: {json_path}")
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Неверный JSON в {specialization}: {json_path} - {e}")
        raise ValueError(f"Ошибка в файле вопросов {specialization}: {e}")
    
    # Парсинг в модели Question
    questions = []
    for item in data:
        opts = item["options"]
        correct_str = item["correct_answers"].split(",")
        correct = {int(x.strip()) for x in correct_str}
        
        q = Question(
    question=item["question"],
    options=opts,
    correct_answers=correct,
    difficulty=Difficulty(difficulties_map.get(item.get("difficulty", "basic"), "BASIC"))
        )
        questions.append(q)
    
    # Выбор нужного количества по уровню
    count = settings.difficulty_questions[difficulty.value]
    if len(questions) < count:
        raise ValueError(f"Недостаточно вопросов в {specialization}: {len(questions)} < {count}")
    
    return random.sample(questions, count)
