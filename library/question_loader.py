"""
Загрузка вопросов из JSON файлов специализаций.
Выбор случайного подмножества по уровню сложности.
"""
import json
import random
from pathlib import Path
from typing import List

from config.settings import settings
from .models import Question, Difficulty

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
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Парсинг в модели Question
    questions = []
    for item in data:
        opts = item["options"]
        correct_str = item["correct_answers"].split(",")  # "1,5" -> {1,5}
        correct = {int(x.strip()) for x in correct_str}
        
        q = Question(
            question=item["question"],
            options=opts,
            correct_answers=correct
        )
        questions.append(q)
    
    # Выбор нужного количества по уровню
    count = settings.difficulty_questions[difficulty.value]
    if len(questions) < count:
        raise ValueError(f"Недостаточно вопросов: {len(questions)} < {count}")
    
    return random.sample(questions, count)
