"""
Расчёт результатов тестов для всех специализаций.
"""

from typing import Dict
from library import CurrentTestState

def calculate_test_results(test_state: CurrentTestState) -> Dict:
    """
    Универсальный расчёт результатов.
    
    Args:
        test_state: Состояние теста
        
    Returns:
        Dict: score, total, percent, status, details
    """
    total_questions = len(test_state.questions)
    correct_answers = 0
    
    # Подсчёт правильных ответов
    for i, question in enumerate(test_state.questions):
        user_answer = (test_state.answers_history[i] 
                      if i < len(test_state.answers_history) 
                      else None)
        if user_answer == question.correct_answer:
            correct_answers += 1
    
    score_percent = (correct_answers / total_questions) * 100
    status = "✅ ПРОЙДЕН" if score_percent >= 80 else "❌ НЕ ПРОЙДЕН"
    
    return {
        "score": correct_answers,
        "total": total_questions,
        "percent": round(score_percent, 1),
        "status": status,
        "details": f"{correct_answers}/{total_questions}"
    }
