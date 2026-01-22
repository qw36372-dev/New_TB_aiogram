"""
Пакет library — закрытая библиотека вопросов, утилиты, модели.
Импортирует все ключевые компоненты для удобства.
"""

from .models import (
    CurrentTestState,
    Difficulty,
    Question,
    AnswerOption,
    UserData,
    TestResult
)
from .question_loader import load_questions_for_specialization
from .stats import StatsManager
from .certificates import generate_certificate
from .keyboards import (
    get_main_keyboard,
    get_difficulty_keyboard,
    get_test_keyboard,
    get_finish_keyboard
)
from .states import TestStates
from .timers import TestTimer
from .anti_spam import AntiSpamMiddleware

from .library import (
    show_first_question, handle_answer_toggle, handle_next_question,
    safe_start_question, show_question, finish_test, toggle_logic
)

__all__ = [
    "CurrentTestState",
    "Difficulty",
    "Question",
    "AnswerOption",
    "UserData",
    "TestResult",
    "load_questions_for_specialization",
    "StatsManager",
    "generate_certificate",
    "get_main_keyboard",
    "get_difficulty_keyboard",
    "get_test_keyboard",
    "get_finish_keyboard",
    "TestStates",
    "TestTimer",
    "AntiSpamMiddleware",
    "show_first_question",
    "handle_answer_toggle", 
    "handle_next_question",
    "safe_start_question",
    "show_question",
    "finish_test",
    "toggle_logic"
]
