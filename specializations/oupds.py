"""
specializations/oupds.py: Хэндлеры для ООУПДС теста.
Шаблон: копипаст + rename spec="ispolniteli", oupds_router → ...
Full FSM: name/pos/dept/diff → test + timer + toggle + PDF.
"""
import asyncio
import logging
import random
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from config.settings import settings
from library import (
    TestStates, Difficulty, load_questions_for_specialization, create_timer,
    get_main_keyboard, get_difficulty_keyboard,
    handle_answer_toggle, handle_next_question, finish_test
)

logger = logging.getLogger(__name__)
oupds_router = Router()

@oupds_router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    """Старт → главное меню."""
    await message.answer("Выберите специализацию:", reply_markup=get_main_keyboard())

@oupds_router.callback_query(F.data.startswith("spec_oupds"))
async def select_oupds(callback: CallbackQuery, state: FSMContext):
    """Ооупдс → ФИО."""
    await callback.message.edit_text("Введите ФИО:")
    await state.set_state(TestStates.waiting_name)
    await callback.answer()

# FSM handlers
@oupds_router.message(StateFilter(TestStates.waiting_name))
async def process_name(message: Message, state: FSMContext):
    """ФИО → должность."""
    await state.update_data(full_name=message.text.strip())
    await message.answer("Должность:")
    await state.set_state(TestStates.waiting_position)

@oupds_router.message(StateFilter(TestStates.waiting_position))
async def process_position(message: Message, state: FSMContext):
    """Должность → отдел."""
    await state.update_data(position=message.text.strip())
    await message.answer("Отдел:")
    await state.set_state(TestStates.waiting_department)

@oupds_router.message(StateFilter(TestStates.waiting_department))
async def process_department(message: Message, state: FSMContext):
    """Отдел → сложность."""
    await state.update_data(department=message.text.strip())
    await message.answer("Уровень сложности:", reply_markup=get_difficulty_keyboard())
    await state.set_state(TestStates.waiting_difficulty)

@oupds_router.callback_query(F.data.startswith("diff_"), StateFilter(TestStates.waiting_difficulty))
async def select_difficulty(callback: CallbackQuery, state: FSMContext):
    """Сложность → загрузка + первый вопрос."""
    diff_name = callback.data.split("_")[1]
    try:
        difficulty = Difficulty(diff_name)
    except ValueError:
        await callback.answer("❌ Неверный уровень")
        return
    
    user_data = await state.get_data()
    user_data["difficulty"] = difficulty
    await state.update_data(user_data)
    
    # Загрузка + shuffle
    questions = load_questions_for_specialization("oupds", difficulty, callback.from_user.id)
    if not questions:
        await callback.message.edit_text("❌ Нет вопросов")
        return
    
    test_state = CurrentTestState(
        questions=questions,
        specialization="oupds",
        difficulty=difficulty,
        full_name=user_data.get("full_name", ""),
        position=user_data.get("position", ""),
        department=user_data.get("department", "")
    )
    
    # Timer
    timer = create_timer(difficulty)
    async def timeout_cb():
        await finish_test(callback.message, test_state)
    await timer.start(timeout_cb)
    test_state.timer_task = timer
    
    await state.update_data(test_state=test_state)
    await handle_next_question(callback, test_state, user_data)  # Показ 1го вопроса

@oupds_router.callback_query(F.data.startswith("ans_"), StateFilter(TestStates.answering_question))
async def answer_toggle(callback: CallbackQuery, state: FSMContext):
    """Toggle во время теста."""
    data = await state.get_data()
    test_state = data.get("test_state")
    if test_state:
        await handle_answer_toggle(callback, test_state)
        await state.update_data(test_state=test_state)

@oupds_router.callback_query(F.data == "next", StateFilter(TestStates.answering_question))
async def next_question(callback: CallbackQuery, state: FSMContext):
    """Далее."""
    data = await state.get_data()
    test_state = data.get("test_state")
    if test_state:
        await handle_next_question(callback, test_state, data)

# Finish callbacks (stub)
@oupds_router.callback_query(F.data == "cert")
async def generate_cert(callback: CallbackQuery):
    await callback.answer("📄 PDF готов! (stub)")

@oupds_router.callback_query(F.data.in_({"new_test", "main", "close"}))
async def finish_actions(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if callback.data == "main":
        await callback.message.edit_text("Главное меню:", reply_markup=get_main_keyboard())
    else:
        await callback.message.delete()
    await callback.answer()
