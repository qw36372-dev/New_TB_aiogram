"""
Роутер ООУПДС — ✅ PROD: 30 вопросов, автоудаление ПРИ "Далее", результаты+сертификат.
✅ ФИКС: delete ТОЛЬКО в next_handler (toggle — edit_markup)
✅ ФИКС: Импорты + finish_test_handler
✅ Чистый чат + FSM данные для Pydantic
"""
import asyncio
import logging
from typing import Dict
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from config.settings import settings
from library import (
    TestStates, get_main_keyboard, get_difficulty_keyboard, load_questions_for_specialization,
    Difficulty, CurrentTestState, TestTimer, UserData, AntiSpamMiddleware,
    show_first_question, handle_answer_toggle, handle_next_question, 
    safe_start_question, finish_test, calculate_test_results  # Все импорты
)
from assets.logo import get_logo_text

logger = logging.getLogger(__name__)

oupds_router = Router()
oupds_router.message.middleware(AntiSpamMiddleware())

oupds_TEST_STATES: Dict[int, CurrentTestState] = {}

async def timeout_callback(bot, chat_id: int, user_id: int):
    """Таймаут."""
    try:
        await bot.send_message(chat_id, "⏰ <b>Время вышло!</b>\nТест не сдан. /start", parse_mode="HTML")
    except Exception as e:
        logger.error(f"Timeout {user_id}: {e}")
    finally:
        oupds_TEST_STATES.pop(user_id, None)

# ========================================
# FSM: Сбор данных (unchanged)
# ========================================
@oupds_router.callback_query(F.data == "oupds")
async def start_oupds_test(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer(get_logo_text(), reply_markup=get_main_keyboard())
    await state.set_state(TestStates.waiting_full_name)
    await callback.message.answer("📝 Введите ФИО:")
    await callback.answer()

@oupds_router.message(StateFilter(TestStates.waiting_full_name))
async def process_full_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text.strip())
    await message.delete()
    await state.set_state(TestStates.waiting_position)
    await message.answer("💼 Должность:")

@oupds_router.message(StateFilter(TestStates.waiting_position))
async def process_position(message: Message, state: FSMContext):
    await state.update_data(position=message.text.strip())
    await message.delete()
    await state.set_state(TestStates.waiting_department)
    await message.answer("🏢 Подразделение:")

@oupds_router.message(StateFilter(TestStates.waiting_department))
async def process_department(message: Message, state: FSMContext):
    data = await state.get_data()
    data["department"] = message.text.strip()
    data["specialization"] = "oupds"
    await message.delete()
    await state.update_data(**data)
    await state.set_state(TestStates.answering_question)
    await message.answer("⚙️ Сложность:", reply_markup=get_difficulty_keyboard())

# ========================================
# ✅ Инициализация теста
# ========================================
@oupds_router.callback_query(F.data.startswith("diff_"))
async def select_difficulty(callback: CallbackQuery, state: FSMContext):
    try:
        diff_name = callback.data.split("_", 1)[1]
        difficulty = Difficulty(diff_name)
        questions = load_questions_for_specialization("oupds", difficulty, callback.from_user.id)
        if not questions:
            return await callback.answer("❌ Вопросы не найдены!")

        data = await state.get_data()
        user_data = UserData(**data, difficulty=difficulty)

        timer = TestTimer(callback.bot, callback.message.chat.id, callback.from_user.id, difficulty)
        await timer.start(lambda: asyncio.create_task(
            timeout_callback(callback.bot, callback.message.chat.id, callback.from_user.id)
        ))

        test_state = CurrentTestState(
            user_id=callback.from_user.id, questions=questions, current_question_idx=0,
            timer=timer, answers_history=[], selected_answers=None
        )
        oupds_TEST_STATES[callback.from_user.id] = test_state

        await callback.message.delete()
        await callback.message.answer("🚀 <b>Тест начат!</b>", parse_mode="HTML")
        await show_first_question(callback.message, test_state)
        await callback.answer()
        logger.info(f"✅ Тест oupds {callback.from_user.id}")
    except Exception as e:
        logger.error(f"Difficulty error: {e}")
        await callback.answer("❌ Инициализация")

# ========================================
# ✅ ТОГГЛ: Выбор ответа (EDIT, НЕ delete)
# ========================================
@oupds_router.callback_query(F.data.startswith("toggle_"))
async def toggle_answer(callback: CallbackQuery, state: FSMContext):
    """✅ Выбор: меняем markup на 'Далее' (НЕ delete!)."""
    user_id = callback.from_user.id
    test_state = oupds_TEST_STATES.get(user_id)
    if not test_state:
        return await callback.answer("❌ Сессия истекла")

    await callback.answer("Выбрано ✓")

    # ✅ TestMixin toggle
    await handle_answer_toggle(callback, test_state)

    # ✅ Меняем клавиатуру: только "Далее"
    next_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡️ Далее", callback_data="next")]
    ])
    await callback.message.edit_reply_markup(reply_markup=next_markup)  # Остаётся в чате!

    logger.info(f"Toggle {user_id}")

# ========================================
# ✅ NEXT: Удаляем + следующий вопрос
# ========================================
@oupds_router.callback_query(F.data == "next")
async def next_question_handler(callback: CallbackQuery, state: FSMContext):
    """✅ Delete ТОЛЬКО здесь + следующий."""
    user_id = callback.from_user.id
    test_state = oupds_TEST_STATES.get(user_id)
    if not test_state:
        return await callback.answer("❌ Сессия истекла")

    await callback.message.delete()  # ✅ Удаляем текущий вопрос

    # ✅ TestMixin: обработка next (покажет следующий или finish)
    await handle_next_question(callback, test_state)
    logger.info(f"Next {user_id}")

# ========================================
# ✅ FINISH: Результаты + сертификат
# ========================================
@oupds_router.callback_query(F.data == "finish_test")
async def finish_test_handler(callback: CallbackQuery, state: FSMContext):
    """✅ Результаты + сертификат + очистка."""
    user_id = callback.from_user.id
    test_state = oupds_TEST_STATES.get(user_id)
    if not test_state:
        return await callback.answer("❌ Сессия истекла")

    try:
        await callback.message.delete()
        data = await state.get_data()
        user_data = UserData(**data, difficulty=test_state.questions[0].difficulty)
        results = calculate_test_results(test_state)
        await finish_test(callback.message, test_state, user_data, results)  # Генерирует сертификат
        
        del oupds_TEST_STATES[user_id]
        await state.clear()
        logger.info(f"✅ Завершён {user_id}")
    except Exception as e:
        logger.error(f"Finish error: {e}")
        await callback.answer("❌ Завершение")
    
    await callback.answer()
