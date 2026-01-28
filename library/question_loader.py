import json
import logging
import random
from pathlib import Path
from typing import List

from config.settings import settings
from .models import Question, Difficulty

logger = logging.getLogger(__name__)

def load_questions_for_specialization(specialization: str, difficulty: Difficulty, seed: int = None) -> List[Question]:
    if seed is not None:
        random.seed(seed)
    
    json_path = settings.questions_dir / f"{specialization}.json"
    if not json_path.exists():
        logger.error(f"JSON не найден: {json_path}")
        return []
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"JSON ошибка {specialization}: {e}")
        return []
    
    questions = []
    for item in 
        try:
            opts = item["options"]
            correct_str = item["correct_answers"].split(",")
            correct = {int(x.strip()) for x in correct_str}
            
            q = Question(
                question=item["question"],
                options=opts,
                correct_answers=correct
                # difficulty=BASIC по умолчанию ✅
            )
            questions.append(q)
        except Exception as e:
            logger.warning(f"Пропуск вопроса: {e}")
            continue
    
    count = settings.difficulty_questions.get(difficulty.value, 30)
    if len(questions) < count:
        logger.warning(f"Мало вопросов {specialization}: {len(questions)} < {count}")
        count = len(questions)
    
    return random.sample(questions, count)
