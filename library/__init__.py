"""
✅ Library: базовые импорты БЕЗ цикла.
Функции library — ленивые (по требованию).
✅ ФИКС: Убраны ссылки на несуществующие функции.
"""

# Базовые (без зависимостей)
from .enum import Difficulty
from .models import (
    CurrentTestState, Question, AnswerOption, UserData, TestResult
)
from .timers import TestTimer
from .question_loader import load_questions_for_specialization
from .stats import StatsManager
from .keyboards import (
    get_main_keyboard, get_difficulty_keyboard, get_test_keyboard, get_finish_keyboard
)
from .states import TestStates
from .anti_spam import AntiSpamMiddleware

# ✅ Ленивые прокси для library функций (только существующие)
def _lazy_import(name):
    """Helper для ленивого импорта."""
    from .library import __dict__ as lib_dict
    return lib_dict[name]

safe_start_question = lambda *a, **kw: _lazy_import('safe_start_question')(*a, **kw)
show_first_question = lambda *a, **kw: _lazy_import('show_first_question')(*a, **kw)
handle_answer_toggle = lambda *a, **kw: _lazy_import('handle_answer_toggle')(*a, **kw)
handle_next_question = lambda *a, **kw: _lazy_import('handle_next_question')(*a, **kw)
show_question_next = lambda *a, **kw: _lazy_import('show_question_next')(*a, **kw)
finish_test = lambda *a, **kw: _lazy_import('finish_test')(*a, **kw)
calculate_test_results = lambda *a, **kw: _lazy_import('calculate_test_results')(*a, **kw)
toggle_logic = lambda *a, **kw: _lazy_import('toggle_logic')(*a, **kw)

# ✅ Сертификат в finish_test()

__all__ = [
    "Difficulty", "CurrentTestState", "Question", "UserData", "TestResult",
    "TestTimer", "load_questions_for_specialization", "StatsManager",
    "get_main_keyboard", "get_difficulty_keyboard", "get_test_keyboard", "get_finish_keyboard",
    "TestStates", "AntiSpamMiddleware",
    "show_first_question", "handle_answer_toggle", "handle_next_question", "show_question_next",
    "finish_test", "toggle_logic", "calculate_test_results",
    "safe_start_question"
]
