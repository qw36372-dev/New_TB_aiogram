"""
library/__init__.py: Все импорты + middlewares.
Production: expose для test_bot_main/specializations.
"""
from typing import Optional
import asyncio
import logging

logger = logging.getLogger(__name__)

# Core models/states/timer
from .models import Question, CurrentTestState, Difficulty, TestStates
from .question_loader import load_questions_for_specialization
from .timers import TestTimer, create_timer
from .library import (  # Core logic
    _show_question, handle_answer_toggle, handle_next_question, finish_test
)

# Keyboards lazy
def get_main_keyboard(): from .keyboards import get_main_keyboard; return get_main_keyboard()
def get_difficulty_keyboard(): from .keyboards import get_difficulty_keyboard; return get_difficulty_keyboard()
def get_test_keyboard(options, selected): from .keyboards import get_test_keyboard; return get_test_keyboard(options, selected)
def get_finish_keyboard(): from .keyboards import get_finish_keyboard; return get_finish_keyboard()

# Fallbacks
def safe_timer_remaining(timer): 
    try: return timer.remaining_time() if hasattr(timer, 'remaining_time') else "∞"
    except: return "∞"

def safe_timer_stop(timer):
    try: getattr(timer, 'stop', lambda: None)()
    except: pass

# Middlewares
from .middlewares import AntiSpamMiddleware, ErrorHandlerMiddleware

# AntiSpam stub (legacy, используй middlewares)
class AntiSpamMiddleware:
    async def __call__(self, handler, event, data):
        from .middlewares import AntiSpamMiddleware as Real
        return await Real()(handler, event, data)

__all__ = [
    "TestStates", "Difficulty", "Question", "CurrentTestState",
    "load_questions_for_specialization", "create_timer",
    "get_main_keyboard", "get_difficulty_keyboard", "get_test_keyboard", "get_finish_keyboard",
    "_show_question", "handle_answer_toggle", "handle_next_question", "finish_test",
    "safe_timer_remaining", "safe_timer_stop",
    "AntiSpamMiddleware", "ErrorHandlerMiddleware"
]
