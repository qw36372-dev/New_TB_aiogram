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
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)

from library.models import (
    CurrentTestState, UserData, TestResult, Question, Difficulty
)
from library.keyboards import get_test_keyboard, get_finish_keyboard
from library.timers import TestTimer  # ✅ Для таймера
from library.stats import StatsManager
from library.certificates import generate_certificate

async def show_first_question(message: Message, test_state: CurrentTestState):
    """✅ ПЕРВЫЙ вопрос БЕЗ проверок сессии."""
    try:
        if not test_state.questions:
            await message.answer("❌ Нет вопросов для теста")
            return
        q = test_state.questions[test_state.current_question_idx]
        
        time_left_seconds = test_state.timer.remaining_seconds()  # ✅ int
        time_left_str = test_state.timer.remaining_time()  # ✅ str для чата
        
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
    """ТОЛЬКО логика toggle, БЕЗ edit/delete!"""
    try:
        idx = int(callback.data.split("_")[1])
        if test_state.selected_answers is None:
            test_state.selected_answers = set()
        if idx in test_state.selected_answers:
            test_state.selected_answers.discard(idx)
        else:
            test_state.selected_answers.add(idx)
        logger.info(f"✅ Toggle {idx} для {test_state.user_id}, selected: {test_state.selected_answers}")
        await callback.answer()  # Только спиннер убрать
    except Exception as e:
        logger.error(f"Toggle logic error: {e}")
        await callback.answer("❌ Ошибка")

async def handle_next_question(callback: CallbackQuery, test_state: CurrentTestState):
    """ТОЛЬКО логика next + сохранение ответа, БЕЗ show/delete"""
    try:
        # ✅ СОХРАНИТЬ ответ перед next!
        if test_state.selected_answers:
            test_state.answers_history.append(test_state.selected_answers.copy())
        test_state.selected_answers = set()
        
        if test_state.current_question_idx + 1 >= len(test_state.questions):
            await finish_test(callback.message, test_state)  # message для finish
            return
        
        test_state.current_question_idx += 1
        logger.info(f"✅ Next to {test_state.current_question_idx + 1} для {test_state.user_id}")
        await callback.answer()
    except Exception as e:
        logger.error(f"Next logic error: {e}")
        await callback.answer("❌ Ошибка")
        
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
        idx = test_state.current_question_idx  # ✅ idx
        q = test_state.questions[idx]
        
        time_left_str = test_state.timer.remaining_time()  # ✅ str, без //
        
        markup = get_test_keyboard(q.options, test_state.selected_answers or set())
        await message.answer(
            f"⏰ Осталось: {time_left_str}\n\n"
            f"<b>Вопрос {idx + 1}/{len(test_state.questions)}:</b>\n\n"
            f"{q.question}",  # ✅ question
            reply_markup=markup,
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
        elapsed_str = await test_state.timer.stop()

        # Подсчёт (answers_history или selected_answers последнего)
        correct = 0
        total_questions = len(test_state.questions)
        # Пример: сохраняйте answers_history в toggle/next
        for i, q in enumerate(test_state.questions):
            user_ans = test_state.answers_history[i] if i < len(test_state.answers_history) else set()
            if user_ans.intersection(q.correct_answers):  # Адаптируйте логику
                correct += 1

        percentage = (correct / total_questions) * 100
        grade = "Отлично" if percentage >= 80 else "Хорошо" if percentage >= 60 else "Удовл."

        test_result = TestResult(
            user_data=UserData(  # ✅ Из FSM или test_state (добавьте поля в models.py)
                full_name=getattr(test_state, 'full_name', 'Не указано'),
                position=getattr(test_state, 'position', 'Не указано'),
                department=getattr(test_state, 'department', 'Не указано'),
                specialization=getattr(test_state, 'specialization', 'Неизвестно'),
                difficulty=getattr(test_state, 'difficulty', Difficulty.BASIC)
            ),
            correct_count=correct,
            total_questions=total_questions,
            grade=grade,
            percentage=percentage,
            elapsed_time=elapsed_str
        )

        StatsManager.save_result(test_result)
        cert_path = generate_certificate(test_result)  # Синхронно или await

        await message.answer(
            f"✅ <b>Тест завершён!</b>\n\n"
            f"Правильных: {correct}/{total_questions} ({percentage:.1f}%)\n"
            f"Оценка: {grade}\n"
            f"Время: {elapsed_str}",
            reply_markup=get_finish_keyboard(),
            parse_mode="HTML"
        )
        await message.answer_document(FSInputFile(cert_path))

        # Cleanup
        if cert_path and os.path.exists(cert_path):
            os.remove(cert_path)
        logger.info(f"✅ Тест завершён для {user_id}: {percentage:.1f}%")
        
    except Exception as e:
        logger.error(f"Finish test error: {e}")
        await message.answer("❌ Ошибка завершения теста")

def toggle_logic(selected: Set[int], total: int) -> bool:
    """Вспомогательная логика toggle."""
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
