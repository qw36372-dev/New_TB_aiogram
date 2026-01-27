"""
Library: общие функции для всех тестовых модулей.
✅ Замена TestMixin — 6 функций для FSM-тестов.
✅ Production-ready: статистика, PDF-сертификат, таймеры, toggle-ответы.
✅ ФИКС: синтаксис finish_test, handle_next_question + user_data, show_question_next.
"""
import asyncio
import logging
import os
from typing import Dict, Any, Set
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)

from .models import (
    CurrentTestState, UserData, TestResult, Question, Difficulty
)
from .keyboards import get_test_keyboard, get_finish_keyboard
from .timers import TestTimer
from .stats import StatsManager
from .certificates import generate_certificate

async def show_first_question(message: Message, test_state: CurrentTestState):
    """✅ ПЕРВЫЙ вопрос."""
    try:
        if not test_state.questions:
            await message.answer("❌ Нет вопросов")
            return
        await _show_question(message, test_state, is_first=True)
        logger.info(f"✅ Первый вопрос {test_state.user_id}")
    except Exception as e:
        logger.error(f"Show first error: {e}")
        await message.answer("❌ Ошибка показа")

async def show_question(message: Message, test_state: CurrentTestState):
    """✅ ОБЫЧНЫЙ вопрос (аналог show_first_question)."""
    await _show_question(message, test_state, is_first=False)

async def _show_question(message: Message, test_state: CurrentTestState, is_first: bool = False):
    """Внутренняя: показ вопроса."""
    q = test_state.questions[test_state.current_question_idx]
    time_left_str = test_state.timer.remaining_time()
    markup = get_test_keyboard(q.options, test_state.selected_answers or set())
    await message.answer(
        f"⏰ Осталось: {time_left_str}\n\n"
        f"<b>Вопрос {test_state.current_question_idx + 1}/{len(test_state.questions)}:</b>\n\n"
        f"{q.question}",
        reply_markup=markup,
        parse_mode="HTML"
    )

async def handle_answer_toggle(callback: CallbackQuery, test_state: CurrentTestState):
    """ТОЛЬКО toggle логика."""
    try:
        idx = int(callback.data.split("_")[1])
        if test_state.selected_answers is None:
            test_state.selected_answers = set()
        if idx in test_state.selected_answers:
            test_state.selected_answers.discard(idx)
        else:
            test_state.selected_answers.add(idx)
        logger.info(f"Toggle {idx} для {test_state.user_id}: {test_state.selected_answers}")
    except Exception as e:
        logger.error(f"Toggle logic error: {e}")
    await callback.answer()

async def handle_next_question(callback: CallbackQuery, test_state: CurrentTestState, user_data: UserData = None):
    """✅ Next: сохраняем + следующий или finish."""
    try:
        # Сохраняем ответ
        if test_state.selected_answers:
            test_state.answers_history.append(test_state.selected_answers.copy())
        test_state.selected_answers = set()
        
        if test_state.current_question_idx + 1 >= len(test_state.questions):
            # Finish
            dummy_msg = Message(chat=callback.message.chat, text="", 
                              message_id=callback.message.message_id, from_user=callback.from_user)
            await finish_test(dummy_msg, test_state, user_data)
            return
        
        test_state.current_question_idx += 1
        await show_question_next(callback, test_state)
        await callback.answer()
    except Exception as e:
        logger.error(f"Next error: {e}")

async def show_question_next(callback: CallbackQuery, test_state: CurrentTestState):
    """✅ Helper: следующий вопрос из callback."""
    try:
        await show_question(callback.message, test_state)
        logger.info(f"✅ Показан вопрос {test_state.current_question_idx} для {test_state.user_id}")
    except Exception as e:
        logger.error(f"Show next error: {e}")

async def finish_test(message: Message, test_state: CurrentTestState, user_data: UserData = None, results: TestResult = None):
    """✅ Результаты + сертификат. ✅ ФИКС: user_data: UserData."""
    try:
        user_id = test_state.user_id
        elapsed_str = test_state.timer.stop()

        # Расчет результатов (если нет results)
        if results is None:
            correct = sum(1 for i, q in enumerate(test_state.questions) 
                         if i < len(test_state.answers_history) and 
                         test_state.answers_history[i] & set(q.correct_answers))
            total = len(test_state.questions)
            percentage = (correct / total) * 100 if total else 0
            grade = "Отлично" if percentage >= 80 else "Хорошо" if percentage >= 60 else "Удовл."
            results = TestResult(user_data or UserData(...), correct_count=correct, total_questions=total,
                                grade=grade, percentage=percentage, elapsed_time=elapsed_str)

        if not user_data:
            user_data = UserData(
                full_name="Не указано", position="Не указано", department="Не указано",
                specialization="oupds", difficulty=test_state.questions[0].difficulty if test_state.questions else Difficulty.BASIC
            )

        StatsManager.save_result(results)
        cert_path = generate_certificate(results)

        await message.answer(
            f"✅ <b>Тест завершён!</b>\nПравильных: {results.correct_count}/{results.total_questions} ({results.percentage:.1f}%)\n"
            f"Оценка: {results.grade}\nВремя: {results.elapsed_time}",
            reply_markup=get_finish_keyboard(), parse_mode="HTML"
        )
        if cert_path and os.path.exists(cert_path):
            await message.answer_document(FSInputFile(cert_path))
            os.remove(cert_path)

        logger.info(f"✅ Завершён {user_id}: {results.percentage:.1f}%")
    except Exception as e:
        logger.error(f"Finish error: {e}")
        await message.answer("❌ Ошибка завершения")

def calculate_test_results(test_state: CurrentTestState) -> TestResult:
    """✅ Расчет результатов для внешнего вызова."""
    # Аналог логики из finish_test
    correct = sum(1 for i, q in enumerate(test_state.questions) 
                 if i < len(test_state.answers_history) and 
                 test_state.answers_history[i] & set(q.correct_answers))
    total = len(test_state.questions)
    percentage = (correct / total) * 100 if total else 0
    grade = "Отлично" if percentage >= 80 else "Хорошо" if percentage >= 60 else "Удовл."
    # Dummy user_data
    user_data = UserData(full_name="Тест", position="", department="", specialization="oupds", difficulty=Difficulty.BASIC)
    return TestResult(user_data=user_data, correct_count=correct, total_questions=total,
                      grade=grade, percentage=percentage, elapsed_time="00:00")

def toggle_logic(selected: Set[int], total: int) -> bool:
    return len(selected) > 0
async def safe_start_question(message: Message, state: FSMContext, test_states: Dict[int, CurrentTestState] = None):
    """✅ Заглушка для старых роутеров: FSM safe + первый вопрос."""
    try:
        user_id = message.from_user.id
        test_state = test_states.get(user_id) if test_states else None
        if not test_state:
            await message.answer("❌ Сессия истекла. /start")
            return
        await show_first_question(message, test_state)
        logger.info(f"✅ Safe start вопрос для {user_id}")
    except Exception as e:
        logger.error(f"Safe start error: {e}")
        await message.answer("❌ Ошибка safe_start")

__all__ = [
    "show_first_question", "show_question", "handle_answer_toggle", "handle_next_question",
    "show_question_next", "finish_test", "calculate_test_results", "toggle_logic",
    "safe_start_question"
]
