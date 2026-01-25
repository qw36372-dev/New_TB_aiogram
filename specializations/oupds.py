"""
Роутер специализации "ООУПДС" — полный тест с FSM для продакшена.
✅ ИСПРАВЛЕНО: локальный oupds_TEST_STATES (без глобальных конфликтов)
✅ ИСПРАВЛЕНО: callback_data "toggle_" и "next" 
✅ УДАЛЕНО: дублирующийся handle_question_message
✅ TestMixin: совместимость с library
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
    safe_start_question,
    finish_test
)
from assets.logo import get_logo_text

logger = logging.getLogger(__name__)

oupds_router = Router()
oupds_router.message.middleware(AntiSpamMiddleware())

# ✅ ЛОКАЛЬНЫЙ словарь состояний для ООУПДС (без конфликтов)
oupds_TEST_STATES: Dict[int, CurrentTestState] = {}

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
        if user_id in oupds_TEST_STATES:
            del oupds_TEST_STATES[user_id]

# ========================================
# ✅ FSM: Сбор данных пользователя (БЕЗ ИЗМЕНЕНИЙ)
# ========================================
@oupds_router.callback_query(F.data == "oupds")
async def start_oupds_test(callback: CallbackQuery, state: FSMContext):
    """Начало теста - ООУПДС."""
    try:
        await callback.message.delete()
        await callback.message.answer(get_logo_text(), reply_markup=get_main_keyboard())
        await state.set_state(TestStates.waiting_full_name)
        await callback.message.answer("📝 Введите ФИО:")
        await callback.answer()
    except Exception as e:
        logger.error(f"Start oupds test error: {e}")
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
        data["specialization"] = "oupds"  # ✅ Специализация
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

# ========================================
# ✅ ИНИЦИАЛИЗАЦИЯ ТЕСТА (ИСПРАВЛЕНО)
# ========================================
@oupds_router.callback_query(F.data.startswith("diff_"))
async def select_difficulty(callback: CallbackQuery, state: FSMContext):
    """Инициализация теста по сложности."""
    try:
        _, diff_name = callback.data.split("_", 1)
        difficulty = Difficulty(diff_name)

        # 1. Загрузка вопросов
        questions = load_questions_for_specialization("oupds", difficulty, callback.from_user.id)
        if not questions:
            await callback.answer("❌ Вопросы не найдены!")
            return

        # 2. Данные пользователя
        data = await state.get_data()
        user_data = UserData(**data, difficulty=difficulty)

        # 3. Таймер
        timer = TestTimer(callback.bot, callback.message.chat.id, callback.from_user.id, difficulty)
        await timer.start(lambda: asyncio.create_task(
            timeout_callback(callback.bot, callback.message.chat.id, callback.from_user.id)
        ))

        # 4. ✅ ПОЛНАЯ инициализация test_state
        test_state = CurrentTestState(
            user_id=callback.from_user.id,
            questions=questions,
            current_question_idx=0,
            timer=timer,
            answers_history=[],
            selected_answers=None
        )
        oupds_TEST_STATES[callback.from_user.id] = test_state  # ✅ Локальный словарь

        # 5. ✅ ПОКАЗ "Тест начат!" + ПЕРВЫЙ вопрос
        await callback.message.delete()
        await callback.message.answer("🚀 <b>Тест начат!</b>", parse_mode="HTML")
        
        # ✅ TestMixin: первый вопрос БЕЗ проверок!
        await show_first_question(callback.message, test_state)
        await callback.answer()
        
        logger.info(f"✅ Тест oupds запущен для {callback.from_user.id}")
        
    except Exception as e:
        logger.error(f"Select difficulty error: {e}")
        await callback.answer("❌ Ошибка инициализации теста")

# ========================================
# ✅ TestMixin: обработчики вопросов (ИСПРАВЛЕНО)
# ========================================
@oupds_router.callback_query(F.data.startswith("toggle_"))
async def toggle_answer(callback: CallbackQuery, state: FSMContext):
    """Переключение выбора ответа. ✅ TestMixin + локальный словарь"""
    user_id = callback.from_user.id
    test_state = oupds_TEST_STATES.get(user_id)
    if test_state:
        await handle_answer_toggle(callback, test_state)
    else:
        await callback.answer("❌ Сессия истекла")
    await callback.answer()

@oupds_router.callback_query(F.data == "next")
async def next_question_handler(callback: CallbackQuery, state: FSMContext):
    """Переход к следующему вопросу. ✅ TestMixin + локальный словарь"""
    user_id = callback.from_user.id
    test_state = oupds_TEST_STATES.get(user_id)
    if test_state:
        await handle_next_question(callback, test_state)
    else:
        await callback.answer("❌ Сессия истекла")
    await callback.answer()

# ========================================
# ✅ TestMixin: стандартные вопросы
# ========================================
# ✅ УДАЛЕНО: handle_question_message - дублирует safe_start_question из TestMixin
# safe_start_question вызывается из library автоматически при необходимости
