"""
Общий миксин для всех тестовых роутеров.
Решение проблемы "Сессия истекла" после "Тест начат!".
Полная замена дублирующегося кода из 11 роутеров.
"""
import asyncio
import logging
import os
from typing import Set
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext

from . import (
    get_test_keyboard, get_finish_keyboard, CurrentTestState, TestResult,
    UserData, StatsManager, generate_certificate
)
logger = logging.getLogger(__name__)

stats_manager = StatsManager()

class TestMixin:
    """Миксин для всех роутеров тестов. Содержит ВСЕ общие методы."""
    
    async def show_first_question(self, message: Message, test_state: CurrentTestState):
        """✅ ПЕРВЫЙ вопрос БЕЗ проверок сессии."""
        try:
            user_id = test_state.user_id
            q = test_state.questions[0]
            
            time_left = test_state.timer.remaining_time()
            options_text = "\n".join([f"{i}. {opt}" for i, opt in enumerate(q.options, 1)])

            await message.answer(
                f"⏰ <b>{int(time_left)}</b>с\n\n"
                f"❓ <b>Вопрос 1/{len(test_state.questions)}:</b>\n"
                f"{q.question}\n\n"
                f"{options_text}",
                reply_markup=get_test_keyboard(set()),
                parse_mode="HTML"
            )
            logger.info(f"✅ Первый вопрос показан для {user_id}")
        except Exception as e:
            logger.error(f"Show first question error: {e}")
            await message.answer("❌ Ошибка показа вопроса")
    
    async def safe_start_question(self, message: Message, state: FSMContext, TEST_STATES: dict):
        """Стандартный start_question с проверками."""
        try:
            user_id = message.from_user.id
            if user_id not in TEST_STATES:
                await message.answer("❌ Сессия теста истекла. Начните заново.")
                return
                
            test_state = TEST_STATES[user_id]
            if test_state.current_question_idx >= len(test_state.questions):
                await self.finish_test(message, state, TEST_STATES)
                return

            q = test_state.questions[test_state.current_question_idx]
            time_left = test_state.timer.remaining_time()
            options_text = "\n".join([f"{i}. {opt}" for i, opt in enumerate(q.options, 1)])

            await message.answer(
                f"⏰ <b>{int(time_left)}</b>с\n\n"
                f"❓ <b>Вопрос {test_state.current_question_idx + 1}/{len(test_state.questions)}:</b>\n"
                f"{q.question}\n\n"
                f"{options_text}",
                reply_markup=get_test_keyboard(test_state.selected_answers or set()),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Safe start question error: {e}")
            await message.answer("❌ Ошибка отображения вопроса")
    
    async def handle_answer_toggle(self, callback: CallbackQuery, TEST_STATES: dict):
        """Обработка выбора/снятия ответа."""
        try:
            _, idx_str = callback.data.split("_")
            idx = int(idx_str)
            user_id = callback.from_user.id

            if user_id not in TEST_STATES:
                await callback.answer("❌ Сессия истекла")
                return

            test_state = TEST_STATES[user_id]
            if test_state.selected_answers is None:
                test_state.selected_answers: Set[int] = set()

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
    
    async def handle_next_question(self, callback: CallbackQuery, state: FSMContext, TEST_STATES: dict):
        """Переход к следующему вопросу."""
        try:
            user_id = callback.from_user.id
            if user_id not in TEST_STATES:
                await callback.answer("❌ Сессия истекла")
                return

            test_state = TEST_STATES[user_id]
            test_state.answers_history.append(test_state.selected_answers or set())
            test_state.current_question_idx += 1
            test_state.selected_answers = None

            await callback.message.delete()
            await self.safe_start_question(callback.message, state, TEST_STATES)
            await callback.answer()
        except Exception as e:
            logger.error(f"Next question error: {e}")
            await callback.answer("❌ Ошибка перехода")
    
    async def finish_test(self, message: Message, state: FSMContext, TEST_STATES: dict):
        """Завершение теста: подсчёт, сохранение, PDF."""
        try:
            user_id = message.from_user.id
            if user_id not in TEST_STATES:
                return

            test_state = TEST_STATES[user_id]
            elapsed = await test_state.timer.stop()

            data = await state.get_data()
            user_data = UserData(**data)

            # Подсчёт
            correct = 0
            total_questions = len(test_state.questions)
            for i, q in enumerate(test_state.questions):
                user_answers = test_state.answers_history[i] if i < len(test_state.answers_history) else set()
                if user_answers == q.correct_answers:
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

            await stats_manager.save_result(test_result)
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

            await state.clear()
            del TEST_STATES[user_id]
            asyncio.create_task(asyncio.to_thread(os.remove, cert_path))
            
        except Exception as e:
            logger.error(f"Finish test error: {e}")
            await message.answer("❌ Ошибка завершения теста")
