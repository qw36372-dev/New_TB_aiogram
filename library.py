"""
Library: общие функции для всех тестовых модулей.
✅ TestMixin функционал: show_first_question, handle_answer_toggle и др.
"""
import logging
from typing import Dict, Any
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config.settings import settings  # Если нужен
from . import TestStates, CurrentTestState  # Импорты ваших классов

logger = logging.getLogger(__name__)

# ========================================
# ✅ TestMixin: основные функции
# ========================================
async def show_first_question(message: Message, test_state: CurrentTestState):
    """Показ первого вопроса (специально без проверок)."""
    try:
        if test_state.current_question_idx >= len(test_state.questions):
            return
        
        question = test_state.questions[test_state.current_question_idx]
        markup = question.get_keyboard_markup(test_state.selected_answers)
        
        await message.answer(
            f"❓ <b>Вопрос {test_state.current_question_idx + 1}/{len(test_state.questions)}</b>\n\n"
            f"{question.text}",
            reply_markup=markup,
            parse_mode="HTML"
        )
        logger.info(f"Показан вопрос {test_state.current_question_idx + 1} для {test_state.user_id}")
    except Exception as e:
        logger.error(f"Show first question error: {e}")

async def handle_answer_toggle(callback: CallbackQuery, test_states: Dict[int, CurrentTestState]):
    """Переключение выбора ответа."""
    try:
        user_id = callback.from_user.id
        if user_id not in test_states:
            await callback.answer("❌ Тест не найден!")
            return
            
        test_state = test_states[user_id]
        _, q_idx_str, a_idx_str = callback.data.split("_")
        q_idx, a_idx = int(q_idx_str), int(a_idx_str)
        
        # ✅ Toggle логика
        test_state.selected_answers = toggle_logic(test_state.selected_answers, q_idx, a_idx)
        
        # Обновить клавиатуру
        question = test_state.questions[q_idx]
        markup = question.get_keyboard_markup(test_state.selected_answers)
        await callback.message.edit_reply_markup(reply_markup=markup)
        await callback.answer()
    except Exception as e:
        logger.error(f"Toggle answer error: {e}")

async def handle_next_question(callback: CallbackQuery, state: FSMContext, test_states: Dict[int, CurrentTestState]):
    """Следующий вопрос."""
    try:
        user_id = callback.from_user.id
        test_state = test_states[user_id]
        
        test_state.answers_history.append(test_state.selected_answers.copy() if test_state.selected_answers else {})
        test_state.selected_answers = {}
        test_state.current_question_idx += 1
        
        if test_state.current_question_idx >= len(test_state.questions):
            await finish_test(callback.message, test_state)
            del test_states[user_id]  # ✅ Очистка
            return
        
        await show_question(callback.message, test_state)
        await callback.answer()
    except Exception as e:
        logger.error(f"Next question error: {e}")

async def safe_start_question(message: Message, state: FSMContext, test_states: Dict[int, CurrentTestState]):
    """Безопасный показ вопроса."""
    user_id = message.from_user.id
    if user_id in test_states:
        await show_question(message, test_states[user_id])

async def show_question(message: Message, test_state: CurrentTestState):
    """Показ любого вопроса."""
    try:
        question = test_state.questions[test_state.current_question_idx]
        markup = question.get_keyboard_markup(test_state.selected_answers or {})
        
        await message.answer(
            f"❓ <b>Вопрос {test_state.current_question_idx + 1}/{len(test_state.questions)}</b>\n\n"
            f"{question.text}",
            reply_markup=markup,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Show question error: {e}")

async def finish_test(message: Message, test_state: CurrentTestState):
    """Завершение теста."""
    try:
        await message.answer("🎉 <b>Тест завершён!</b>\nРезультаты рассчитываются...", parse_mode="HTML")
        # TODO: ваша логика подсчёта баллов и сохранения результатов
        logger.info(f"Тест завершён для {test_state.user_id}")
    except Exception as e:
        logger.error(f"Finish test error: {e}")

# ========================================
# ✅ Вспомогательные функции
# ========================================
def toggle_logic(selected: Dict[int, list], q_idx: int, a_idx: int) -> Dict[int, list]:
    """Логика множественного выбора."""
    if q_idx not in selected:
        selected[q_idx] = []
    if a_idx in selected[q_idx]:
        selected[q_idx].remove(a_idx)
    else:
        selected[q_idx].append(a_idx)
    return selected

# Экспорт для удобства (если используете from library import *)
__all__ = [
    "show_first_question", "handle_answer_toggle", "handle_next_question",
    "safe_start_question", "show_question", "finish_test", "toggle_logic"
]
