"""
Library: общие функции для всех тестовых модулей.
✅ Замена TestMixin из test_mixin.py — 6 функций для FSM-тестов.
✅ Production-ready: статистика, PDF-сертификат, таймеры, toggle-ответы.
✅ ФИКС цикла: ЛОКАЛЬНЫЕ импорты (без from library import)
Использование: from library import show_first_question, finish_test
"""

import asyncio
import logging
import os
from typing import Dict, Any, Set
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)

# ✅ ФИКС: ЛОКАЛЬНЫЕ импорты БЕЗ цикла (from .models, НЕ from library)
from .models import (
    CurrentTestState, UserData, TestResult, Question, Difficulty
)
from .keyboards import get_test_keyboard, get_finish_keyboard
from .timers import TestTimer
from .stats import StatsManager
from .certificates import generate_certificate

async def show_first_question(message: Message, test_state: CurrentTestState):
    """✅ ПЕРВЫЙ вопрос БЕЗ проверок сессии."""
    try:
        if not test_state.questions:
            await message.answer("❌ Нет вопросов для теста")
            return
        q = test_state.questions[test_state.current_question_idx]
        
        time_left_seconds = test_state.timer.remaining_seconds()
        time_left_str = test_state.timer.remaining_time()
        
        markup = get_test_keyboard(q.options, test_state.selected_answers or set())
        await message.answer(
            f"⏰ Осталось: {time_left_str}\n\n"
            f"<b>Вопрос {test_state.current_question_idx + 1}/{len(test_state.questions)}:</b>\n\n"
            f"{q.question}",
            reply_markup=markup,
            parse_mode="HTML"
        )
        logger.info(f"✅ Первый вопрос показан для {test_state.user_id}")
    except Exception as e:
        logger.error(f"Show first question error: {e}")
        await message.answer("❌ Ошибка показа вопроса")

async def handle_answer_toggle(callback: CallbackQuery, test_state: CurrentTestState):
    """ТОЛЬКО логика toggle, БЕЗ edit/delete/show!"""
    try:
        idx = int(callback.data.split("_")[1])
        if test_state.selected_answers is None:
            test_state.selected_answers = set()
        if idx in test_state.selected_answers:
            test_state.selected_answers.discard(idx)
        else:
            test_state.selected_answers.add(idx)
        logger.info(f"✅ Toggle {idx} для {test_state.user_id}, selected: {test_state.selected_answers}")
        await callback.answer()
    except Exception as e:
        logger.error(f"Toggle logic error: {e}")
        await callback.answer("❌ Ошибка")

async def handle_next_question(callback: CallbackQuery, test_state: CurrentTestState, message: Message):
    """Логика next + show следующего (или finish). ФИКС: + message для show."""
    try:
        # ✅ СОХРАНИТЬ ответ
        if test_state.selected_answers:
            test_state.answers_history.append(test_state.selected_answers.copy())
        test_state.selected_answers = set()
        
        if test_state.current_question_idx + 1 >= len(test_state.questions):
            await finish_test(message, test_state)
            return
        
        test_state.current_question_idx += 1
        logger.info(f"✅ Next to {test_state.current_question_idx + 1} для {test_state.user_id}")
        await show_question(message, test_state)  # ✅ Показываем следующий
        await callback.answer()
    except Exception as e:
        logger.error(f"Next logic error: {e}")
        await callback.answer("❌ Ошибка")

async def safe_start_question(message: Message, state: FSMContext, test_states: Dict[int, CurrentTestState]):
    """Защита от некорректных состояний."""
    user_id = message.from_user.id
    if user_id in test_states:
        test_state = test_states[user_id]
        await show_question(message, test_state)
    else:
        await message.answer("❌ Сессия теста истекла. /start")

async def show_question(message: Message, test_state: CurrentTestState):
    """Показ текущего вопроса."""
    try:
        user_id = test_state.user_id
        idx = test_state.current_question_idx
        q = test_state.questions[idx]
        
        time_left_str = test_state.timer.remaining_time()
        
        markup = get_test_keyboard(q.options, test_state.selected_answers or set())
        await message.answer(
            f"⏰ Осталось: {time_left_str}\n\n"
            f"<b>Вопрос {idx + 1}/{len(test_state.questions)}:</b>\n\n"
            f"{q.question}",
            reply_markup=markup,
            parse_mode="HTML"
        )
        logger.info(f"✅ Показан вопрос {idx+1} для {user_id}")
    except Exception as e:
        logger.error(f"Show question error: {e}")
        await message.answer("❌ Ошибка показа вопроса")

async def finish_test(message: Message, test_state: CurrentTestState):
    """Завершение: подсчёт, PDF. ФИКС: user_data из FSM."""
    try:
        user_id = test_state.user_id
        elapsed_str = await test_state.timer.stop()

        # Подсчёт
        correct = 0
        total = len(test_state.questions)
        for i, q in enumerate(test_state.questions):
            user_ans = test_state.answers_history[i] if i < len(test_state.answers_history) else set()
            if user_ans & set(q.correct_answers):  # ✅ Set intersection
                correct += 1

        percentage = (correct / total) * 100
        grade = "Отлично" if percentage >= 80 else "Хорошо" if percentage >= 60 else "Удовл."

        # ✅ UserData из test_state (добавьте поля в CurrentTestState если нужно)
        test_result = TestResult(
            user_data=UserData(
                full_name=getattr(test_state, 'full_name', 'Не указано'),
                position=getattr(test_state, 'position', 'Не указано'),
                department=getattr(test_state, 'department', 'Не указано'),
                specialization=getattr(test_state, 'specialization', 'oupds'),
                difficulty=test_state.questions[0].difficulty if test_state.questions else Difficulty.BASIC
            ),
            correct_count=correct,
            total_questions=total,
            grade=grade,
            percentage=percentage,
            elapsed_time=elapsed_str
        )

        StatsManager.save_result(test_result)
        cert_path = generate_certificate(test_result)

        await message.answer(
            f"✅ <b>Тест завершён!</b>\n\n"
            f"Правильных: {correct}/{total} ({percentage:.1f}%)\n"
            f"Оценка: {grade}\n"
            f"Время: {elapsed_str}",
            reply_markup=get_finish_keyboard(),
            parse_mode="HTML"
        )
        if cert_path:
            await message.answer_document(FSInputFile(cert_path))
            os.remove(cert_path)

        logger.info(f"✅ Тест завершён для {user_id}: {percentage:.1f}%")
    except Exception as e:
        logger.error(f"Finish test error: {e}")
        await message.answer("❌ Ошибка завершения")

def toggle_logic(selected: Set[int], total: int) -> bool:
    return len(selected) > 0

__all__ = [
    "show_first_question",
    "handle_answer_toggle",
    "handle_next_question",
    "safe_start_question",
    "show_question",
    "finish_test",
    "toggle_logic"
]
