"""
Роутер "ООУПДС" — ✅ ПРОДАКШЕН: 30 вопросов + чистый чат + результаты!
Изменения:
✅ oupds_TEST_STATES (локальный)
✅ toggle_ / next / finish_test хэндлеры
✅ callback.message.delete() везде
✅ user_data из FSM для Pydantic
"""
import asyncio
import logging
from typing import Dict
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from config.settings import settings
from library import (
    TestStates,
    get_main_keyboard,
    get_difficulty_keyboard,
    load_questions_for_specialization,
    Difficulty,
    CurrentTestState,
    TestTimer,
    UserData,
    AntiSpamMiddleware,
    show_first_question,
    handle_answer_toggle,
    handle_next_question,
    finish_test,           # ✅ Для финала
    calculate_test_results # ✅ Для результатов
)
from assets.logo import get_logo_text

logger = logging.getLogger(__name__)

oupds_router = Router()
oupds_router.message.middleware(AntiSpamMiddleware())

# ✅ ЛОКАЛЬНЫЙ словарь состояний
oupds_TEST_STATES: Dict[int, CurrentTestState] = {}

async def timeout_callback(bot, chat_id: int, user_id: int):
    """Таймаут теста."""
    try:
        await bot.send_message(
            chat_id,
            "⏰ <b>Время вышло!</b>\n\nТест не сдан. Выберите /start для нового.",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Timeout error user {user_id}: {e}")
    finally:
        if user_id in oupds_TEST_STATES:
            del oupds_TEST_STATES[user_id]

# ========================================
# FSM: Сбор данных (БЕЗ изменений)
# ========================================
@oupds_router.callback_query(F.data == "oupds")
async def start_oupds_test(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.message.delete()
        await callback.message.answer(get_logo_text(), reply_markup=get_main_keyboard())
        await state.set_state(TestStates.waiting_full_name)
        await callback.message.answer("📝 Введите ФИО:")
        await callback.answer()
    except Exception as e:
        logger.error(f"Start oupds error: {e}")
        await callback.answer("❌ Ошибка запуска")

@oupds_router.message(StateFilter(TestStates.waiting_full_name))
async def process_full_name(message: Message, state: FSMContext):
    try:
        await state.update_data(full_name=message.text.strip())
        await message.delete()
        await state.set_state(TestStates.waiting_position)
        await message.answer("💼 Должность:")
    except Exception as e:
        logger.error(f"Full name error: {e}")

@oupds_router.message(StateFilter(TestStates.waiting_position))
async def process_position(message: Message, state: FSMContext):
    try:
        await state.update_data(position=message.text.strip())
        await message.delete()
        await state.set_state(TestStates.waiting_department)
        await message.answer("🏢 Подразделение:")
    except Exception as e:
        logger.error(f"Position error: {e}")

@oupds_router.message(StateFilter(TestStates.waiting_department))
async def process_department(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        data["department"] = message.text.strip()
        data["specialization"] = "oupds"
        await message.delete()
        await state.update_data(**data)
        await state.set_state(TestStates.answering_question)
        await message.answer("⚙️ Выберите уровень сложности:", reply_markup=get_difficulty_keyboard())
    except Exception as e:
        logger.error(f"Department error: {e}")

# ========================================
# Инициализация теста
# ========================================
@oupds_router.callback_query(F.data.startswith("diff_"))
async def select_difficulty(callback: CallbackQuery, state: FSMContext):
    try:
        _, diff_name = callback.data.split("_", 1)
        difficulty = Difficulty(diff_name)

        questions = load_questions_for_specialization("oupds", difficulty, callback.from_user.id)
        if not questions:
            await callback.answer("❌ Вопросы не найдены!")
            return

        data = await state.get_data()
        user_data = UserData(**data, difficulty=difficulty)

        timer = TestTimer(callback.bot, callback.message.chat.id, callback.from_user.id, difficulty)
        await timer.start(lambda: asyncio.create_task(
            timeout_callback(callback.bot, callback.message.chat.id, callback.from_user.id)
        ))

        test_state = CurrentTestState(
            user_id=callback.from_user.id,
            questions=questions,
            current_question_idx=0,
            timer=timer,
            answers_history=[],
            selected_answers=None
        )
        oupds_TEST_STATES[callback.from_user.id] = test_state

        await callback.message.delete()
        await callback.message.answer("🚀 <b>Тест начат!</b>", parse_mode="HTML")
        await show_first_question(callback.message, test_state)
        await callback.answer()
        
        logger.info(f"✅ Тест oupds запущен для {callback.from_user.id}")
        
    except Exception as e:
        logger.error(f"Select difficulty error: {e}")
        await callback.answer("❌ Ошибка инициализации")

# ========================================
# TestMixin хэндлеры + ОЧИСТКА ЧАТА ✅
# ========================================
@oupds_router.callback_query(F.data.startswith("toggle_"))
async def toggle_answer(callback: CallbackQuery, state: FSMContext):
    """Toggle + delete после edit"""
    user_id = callback.from_user.id
    test_state = oupds_TEST_STATES.get(user_id)
    if test_state:
        logger.info(f"🔄 Toggle user={user_id} msg_id={callback.message.message_id}")
        await handle_answer_toggle(callback, test_state)  # ✅ edit сначала
        await callback.message.delete()  # ✅ delete ПОСЛЕ edit
    else:
        await callback.answer("❌ Сессия истекла")
    await callback.answer()
    logger.info("✅ Toggle OK")

@oupds_router.callback_query(F.data == "next")
async def next_question_handler(callback: CallbackQuery, state: FSMContext):
    """Следующий вопрос + очистка"""
    user_id = callback.from_user.id
    test_state = oupds_TEST_STATES.get(user_id)
    if test_state:
        logger.info(f"➡️ Next user={user_id} msg_id={callback.message.message_id}")
        await handle_next_question(callback, test_state)  # ✅ Сначала next
        try:
            await callback.message.delete()  # ✅ Потом delete
        except Exception as e:
            logger.warning(f"Delete после next: {e}")
    else:
        await callback.answer("❌ Сессия истекла")
    await callback.answer()
    logger.info("✅ Next OK")

@oupds_router.callback_query(F.data == "finish_test")
async def finish_test_handler(callback: CallbackQuery, state: FSMContext):
    """Завершение + результаты + очистка."""
    user_id = callback.from_user.id
    test_state = oupds_TEST_STATES.get(user_id)
    
    if test_state:
        try:
            # ✅ user_data из FSM (фикс Pydantic)
            data = await state.get_data()
            user_data = UserData(**data, difficulty=test_state.questions[0].difficulty)
            
            # ✅ Результаты + finish_test
            results = calculate_test_results(test_state)
            await callback.message.delete()  # ✅ Удаляем финальный вопрос
            await finish_test(callback.message, test_state, user_data, results)
            
            # ✅ Очистка
            del oupds_TEST_STATES[user_id]
            await state.clear()
            
        except Exception as e:
            logger.error(f"Finish test error: {e}")
            await callback.answer("❌ Ошибка завершения теста")
    else:
        await callback.answer("❌ Сессия истекла")
    await callback.answer()
