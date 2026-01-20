"""
Роутер специализации "Информатизация и информационная безопасность" — полный тест с FSM для продакшена.
Оптимизировано: устранены дублирования, исправлены импорты, добавлена обработка ошибок.
"""
import asyncio
import logging
import os
from typing import Set
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from config.settings import settings
from library import (
    TestStates, get_main_keyboard, get_difficulty_keyboard,
    get_test_keyboard, get_finish_keyboard, load_questions_for_specialization,
    StatsManager, TestTimer, generate_certificate, TestResult, UserData,
    Difficulty, CurrentTestState, AntiSpamMiddleware
)
from assets.logo import get_logo_text

logger = logging.getLogger(__name__)
stats_manager = StatsManager()
TEST_STATES: dict[int, CurrentTestState] = {}  # Активные тесты пользователей

oupds_router = Router()
oupds_router.message.middleware(AntiSpamMiddleware())

async def timeout_callback(bot, chat_id: int, user_id: int):
    """Обработчик таймаута теста."""
    try:
        await bot.send_message(
            chat_id,
            "⏰ <b>Время вышло!</b>\n\nТест не сдан. Выберите /start для нового.",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Timeout callback error for user {user_id}: {e}")
    finally:
        if user_id in TEST_STATES:
            del TEST_STATES[user_id]

@oupds_router.callback_query(F.data == "oupds")
async def start_oupds_test(callback: CallbackQuery, state: FSMContext):
    """Начало теста - Информатизация и информационная безопасность."""
    try:
        await callback.message.delete()
        await callback.message.answer(get_logo_text(), reply_markup=get_main_keyboard())
        await state.set_state(TestStates.waiting_full_name)
        await callback.message.answer("📝 Введите ФИО:")
        await callback.answer()
    except Exception as e:
        logger.error(f"Start OUPDS test error: {e}")
        await callback.answer("❌ Ошибка запуска теста")

@oupds_router.message(StateFilter(TestStates.waiting_full_name))
async def process_full_name(message: Message, state: FSMContext):
    """Сохранение ФИО."""
    try:
        await state.update_data(full_name=message.text.strip())
        await message.delete()
        await state.set_state(TestStates.waiting_position)
        await message.answer("💼 Должность:")
    except Exception as e:
        logger.error(f"Process full name error: {e}")
        await message.answer("❌ Ошибка сохранения данных")

@oupds_router.message(StateFilter(TestStates.waiting_position))
async def process_position(message: Message, state: FSMContext):
    """Сохранение должности."""
    try:
        await state.update_data(position=message.text.strip())
        await message.delete()
        await state.set_state(TestStates.waiting_department)
        await message.answer("🏢 Подразделение:")
    except Exception as e:
        logger.error(f"Process position error: {e}")
        await message.answer("❌ Ошибка сохранения данных")

@oupds_router.message(StateFilter(TestStates.waiting_department))
async def process_department(message: Message, state: FSMContext):
    """Переход к выбору сложности."""
    try:
        data = await state.get_data()
        data["department"] = message.text.strip()
        data["specialization"] = "oupds"
        await message.delete()
        await state.update_data(**data)
        await state.set_state(TestStates.answering_question)
        await message.answer(
            "⚙️ Выберите уровень сложности:",
            reply_markup=get_difficulty_keyboard()
        )
    except Exception as e:
        logger.error(f"Process department error: {e}")
        await message.answer("❌ Ошибка перехода к тесту")

@oupds_router.callback_query(F.data.startswith("diff_"))
async def select_difficulty(callback: CallbackQuery, state: FSMContext):
    """Инициализация теста по сложности."""
    try:
        _, diff_name = callback.data.split("_", 1)
        difficulty = Difficulty(diff_name)

        # Загрузка вопросов
        questions = load_questions_for_specialization("oupds", difficulty, callback.from_user.id)
        if not questions:
            await callback.answer("❌ Вопросы не найдены!")
            return

        data = await state.get_data()
        user_data = UserData(
            **data,
            difficulty=difficulty
        )

        # Таймер
        timer = TestTimer(callback.bot, callback.message.chat.id, callback.from_user.id, difficulty)
        await timer.start(lambda: asyncio.create_task(
            timeout_callback(callback.bot, callback.message.chat.id, callback.from_user.id)
        ))

        # Состояние теста
        test_state = CurrentTestState(
            user_id=callback.from_user.id,
            questions=questions,
            timer=timer,
            answers_history=[]
        )
        TEST_STATES[callback.from_user.id] = test_state

        await callback.message.delete()
        await callback.message.answer("🚀 <b>Тест начат!</b>", parse_mode="HTML")
        await start_question(callback.message, state)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Select difficulty error: {e}")
        await callback.answer("❌ Ошибка инициализации теста")

async def start_question(message: Message, state: FSMContext):
    """Отображение текущего вопроса."""
    try:
        user_id = message.from_user.id
        if user_id not in TEST_STATES:
            await message.answer("❌ Сессия теста истекла. Начните заново.")
            return
            
        test_state = TEST_STATES[user_id]

        if test_state.current_question_idx >= len(test_state.questions):
            await finish_test(message, state)
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
        logger.error(f"Start question error: {e}")
        await message.answer("❌ Ошибка отображения вопроса")

@oupds_router.callback_query(F.data.startswith("ans_"))
async def toggle_answer(callback: CallbackQuery, state: FSMContext):
    """Переключение выбора ответа."""
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

@oupds_router.callback_query(F.data == "next_question")
async def next_question(callback: CallbackQuery, state: FSMContext):
    """Переход к следующему вопросу."""
    try:
        user_id = callback.from_user.id
        if user_id not in TEST_STATES:
            await callback.answer("❌ Сессия истекла")
            return

        test_state = TEST_STATES[user_id]

        # Сохраняем ответы текущего вопроса
        test_state.answers_history.append(test_state.selected_answers or set())
        test_state.current_question_idx += 1
        test_state.selected_answers = None

        await callback.message.delete()
        await start_question(callback.message, state)
        await callback.answer()
    except Exception as e:
        logger.error(f"Next question error: {e}")
        await callback.answer("❌ Ошибка перехода")

async def finish_test(message: Message, state: FSMContext):
    """Завершение теста: подсчёт, сохранение, PDF."""
    try:
        user_id = message.from_user.id
        if user_id not in TEST_STATES:
            return

        test_state = TEST_STATES[user_id]
        elapsed = await test_state.timer.stop()

        data = await state.get_data()
        user_data = UserData(**data)

        # Подсчёт правильных ответов
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

        # Сохранение в SQLite
        await stats_manager.save_result(test_result)

        # Генерация сертификата
        cert_path = await generate_certificate(test_result)

        # Показ результатов
        await message.answer(
            f"✅ <b>Тест завершён!</b>\n\n"
            f"Правильных: {correct}/{total_questions} ({score_percent:.1f}%)\n"
            f"Время: {elapsed:.0f}с\n\n"
            f"Ваш сертификат готов!",
            reply_markup=get_finish_keyboard(),
            parse_mode="HTML"
        )

        # Отправка PDF
        await message.answer_document(FSInputFile(cert_path))

        # Очистка
        await state.clear()
        if user_id in TEST_STATES:
            del TEST_STATES[user_id]

        # Удаление временного PDF
        asyncio.create_task(asyncio.to_thread(os.remove, cert_path))
        
    except Exception as e:
        logger.error(f"Finish test error: {e}")
        await message.answer("❌ Ошибка завершения теста")
