"""
Library: общие функции для всех тестовых модулей.
✅ Замена TestMixin из test_mixin.py — 6 функций для FSM-тестов.
✅ Production-ready: статистика, PDF-сертификат, таймеры, toggle-ответы.
Использование в роутерах: from library import show_first_question, finish_test
"""

import asyncio
import logging
import os
from typing import Dict, Any, Set
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)

from library.models import CurrentTestState
from library.keyboards import get_test_keyboard, get_finish_keyboard
from library.stats import StatsManager
from library.certificates import generate_certificate

async def show_first_question(message: Message, test_state: CurrentTestState):
    """✅ ПЕРВЫЙ вопрос БЕЗ проверок сессии."""
    try:
        user_id = test_state.user_id
        q = test_state.questions[0]  # Первый вопрос
        
        time_left = test_state.timer.remaining_time()
        options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(q.options)])
        
        await message.answer(
            f"⏰ Осталось: {time_left//60}:{time_left%60:02d}\n\n"
            f"❓ <b>Вопрос 1/{len(test_state.questions)}</b>\n"
            f"{q.text}\n\n"
            f"{options_text}",
            reply_markup=get_test_keyboard(set()),
            parse_mode="HTML"
        )
        logger.info(f"✅ Первый вопрос показан для {user_id}")
    except Exception as e:
        logger.error(f"Show first question error: {e}")
        await message.answer("❌ Ошибка показа вопроса")

async def handle_answer_toggle(callback: CallbackQuery, test_state: CurrentTestState):
    """Toggle логика множественного выбора ответов."""
    try:
        idx = int(callback.data.split("_")[1])
        
        if test_state.selected_answers is None:
            test_state.selected_answers = set()
        
        if idx in test_state.selected_answers:
            test_state.selected_answers.discard(idx)
        else:
            test_state.selected_answers.add(idx)
        
        await callback.message.edit_reply_markup(
            reply_markup=get_test_keyboard(test_state.selected_answers)
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Toggle answer error: {e}")
        await callback.answer("❌ Ошибка выбора ответа")

async def handle_next_question(callback: CallbackQuery, test_state: CurrentTestState):
    """Переход к следующему вопросу или finish_test."""
    try:
        current_idx = test_state.current_question_index
        if current_idx + 1 >= len(test_state.questions):
            await finish_test(callback.message, test_state)
            return
        
        test_state.current_question_index += 1
        await show_question(callback.message, test_state)
        await callback.answer()
    except Exception as e:
        logger.error(f"Next question error: {e}")
        await callback.answer("❌ Ошибка перехода")

async def safe_start_question(message: Message, state: FSMContext, test_states: Dict[int, CurrentTestState]):
    """Защита от некорректных состояний во время теста."""
    user_id = message.from_user.id
    if user_id in test_states:
        test_state = test_states[user_id]
        await show_question(message, test_state)
    else:
        await message.answer("❌ Сессия теста истекла. Нажмите /start для нового.")

async def show_question(message: Message, test_state: CurrentTestState):
    """Показ текущего вопроса."""
    try:
        user_id = test_state.user_id
        idx = test_state.current_question_index
        q = test_state.questions[idx]
        
        time_left = test_state.timer.remaining_time()
        options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(q.options)])
        
        await message.answer(
            f"⏰ Осталось: {time_left//60}:{time_left%60:02d}\n\n"
            f"❓ <b>Вопрос {idx+1}/{len(test_state.questions)}</b>\n"
            f"{q.text}\n\n"
            f"{options_text}",
            reply_markup=get_test_keyboard(test_state.selected_answers or set()),
            parse_mode="HTML"
        )
        logger.info(f"✅ Показан вопрос {idx+1} для {user_id}")
    except Exception as e:
        logger.error(f"Show question error: {e}")
        await message.answer("❌ Ошибка показа вопроса")

async def finish_test(message: Message, test_state: CurrentTestState):
    """Завершение теста: подсчёт, сохранение, PDF."""
    try:
        user_id = test_state.user_id
        elapsed = await test_state.timer.stop()

        # UserData из test_state (адаптируйте поля)
        user_data = UserData(
            full_name=test_state.full_name or "",
            position=test_state.position or "",
            department=test_state.department or "",
            specialization=test_state.specialization,
            difficulty=test_state.difficulty
        )

        # Подсчёт из answers_history (если храните по вопросам)
        correct = 0
        total_questions = len(test_state.questions)
        for i, q in enumerate(test_state.questions):
            user_answers = test_state.answers_history[i] if hasattr(test_state, 'answers_history') and i < len(test_state.answers_history) else set()
            if user_answers == set(q.correct_answers):  # set для multiple
                correct += 1

        score_percent = (correct / total_questions) * 100
        test_result = TestResult(
            user_id=user_id,
            specialization=user_data.specialization,
            difficulty=user_data.difficulty,
            score=correct,
            total=total_questions,
            percent=score_percent,
            time_spent=elapsed,
            full_name=user_data.full_name,
            position=user_data.position,
            department=user_data.department
        )

        await StatsManager.save_result(test_result)  # Инстанс или класс-метод
        cert_path = await generate_certificate(test_result)

        await message.answer(
            f"✅ <b>Тест завершён!</b>\n\n"
            f"Правильных: {correct}/{total_questions} ({score_percent:.1f}%)\n"
            f"Время: {elapsed:.0f}с\n\n"
            f"Ваш сертификат готов!",
            reply_markup=get_finish_keyboard(),
            parse_mode="HTML"
        )
        await message.answer_document(FSInputFile(cert_path))

        # Cleanup
        asyncio.create_task(asyncio.to_thread(os.remove, cert_path))
        logger.info(f"✅ Тест завершён для {user_id}")
        
    except Exception as e:
        logger.error(f"Finish test error: {e}")
        await message.answer("❌ Ошибка завершения теста")

def toggle_logic(selected: Set[int], total: int) -> bool:
    """Вспомогательная логика toggle."""
    return len(selected) > 0

# Экспорт для from library import *
__all__ = [
    "show_first_question",
    "handle_answer_toggle",
    "handle_next_question",
    "safe_start_question",
    "show_question",
    "finish_test",
    "toggle_logic"
]
