"""
Загрузка вопросов из JSON файлов специализаций.
Фильтр по уровню сложности + fallback.
Random.sample(count) с user_seed для fairness.
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
    user_id: int = None
) -> List[Question]:
    """
    Загружает вопросы для специализации/сложности.
    Фильтр: q.difficulty == target → fallback все.
    """
    json_path = settings.work_dir / settings.data_dir / f"{specialization}.json"
    
    try:
        with json_path.open("r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, PermissionError) as e:
        logger.error(f"JSON error {specialization}: {e}")
        return []
    
    if not isinstance(raw_data, list):
        logger.error(f"Invalid JSON {specialization}: not list")
        return []
    
    questions = []
    for idx, item in enumerate(raw_data):
        try:
            opts = item.get("options", [])
            if not isinstance(opts, list) or len(opts) < 3:
                logger.warning(f"Skip {specialization}:{idx} invalid options")
                continue
            
            correct_str = item.get("correct_answers", "")
            correct = set(int(x.strip()) for x in correct_str.split(",") if x.strip().isdigit())
            
            q = Question(
                question=item["question"],
                options=opts,
                correct_answers=correct
                # difficulty auto=BASIC из models.py
            )
            questions.append(q)
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"Skip вопрос {specialization}:{idx}: {e}")
            continue
    
    # Фильтр по сложности
    target_diff = difficulty.value
    filtered = [q for q in questions if q.difficulty.value == target_diff]
    
    # Fallback: если мало/нет → все вопросы
    if len(filtered) < 5:
        logger.warning(f"Fallback все вопросы {specialization} (filtered:{len(filtered)})")
        filtered = questions[:]
    
    count = settings.difficulty_questions.get(target_diff, 30)
    if len(filtered) < count:
        logger.warning(f"Мало вопросов {specialization}: {len(filtered)} < {count}")
        count = len(filtered)
    
    # User-seed random для fairness (не всегда один вопрос)
    random.seed(user_id or 42)
    random.shuffle(filtered)
    selected = filtered[:count]
    
    logger.info(f"Загружено {len(selected)}/{count} вопросов {specialization}:{target_diff}")
    return selected
