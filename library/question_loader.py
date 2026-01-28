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
    """
    if seed is not None:
        random.seed(seed)  # Разный порядок для каждого пользователя
    
    json_path = settings.questions_dir / f"{specialization}.json"
    if not json_path.exists():
        logger.error(f"Вопросы не найдены: {json_path}")
        return []
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Неверный JSON в {specialization}: {json_path} - {e}")
        return []
    except Exception as e:
        logger.error(f"Ошибка загрузки {specialization}: {e}")
        return []
    
    # ✅ ПРАВИЛЬНЫЙ цикл с отступами
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
                # difficulty=BASIC по умолчанию
            )
            questions.append(q)
        except KeyError as e:
            logger.warning(f"Пропуск вопроса (нет {e}): {item.get('question', 'N/A')}")
            continue
        except Exception as e:
            logger.warning(f"Ошибка парсинга вопроса: {e}")
            continue
    
    # Выбор нужного количества
    count = getattr(settings, 'difficulty_questions', {}).get(difficulty.value, 30)
    if len(questions) < count:
        logger.warning(f"Недостаточно вопросов {specialization}: {len(questions)} < {count}")
        count = len(questions)
    
    if not questions:
        logger.error(f"Нет вопросов для {specialization}")
        return []
    
    selected = random.sample(questions, count)
    logger.info(f"Загружено {len(selected)} вопросов для {specialization}:{difficulty.value}")
    return selected
