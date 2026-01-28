import asyncio
import logging
from typing import Dict
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from config.settings import settings
from library import (
    TestStates, get_main_keyboard, get_difficulty_keyboard, get_test_keyboard,
    load_questions_for_specialization,
    Difficulty, CurrentTestState, TestTimer, UserData, AntiSpamMiddleware,
    show_first_question, handle_answer_toggle, handle_next_question, 
    finish_test, calculate_test_results
)

from assets.logo import get_logo_text

logger = logging.getLogger(__name__)

oupds_router = Router()
oupds_router.message.middleware(AntiSpamMiddleware())

oupds_TEST_STATES: Dict[int, CurrentTestState] = {}

async def timeout_callback(bot, chat_id: int, user_id: int):
    try:
        await bot.send_message(chat_id, "⏰ <b>Время вышло!</b>\nТест не сдан. /start", parse_mode="HTML")
    except Exception as e:
        logger.error(f"Timeout {user_id}: {e}")
    finally:
        oupds_TEST_STATES.pop(user_id, None)

# FSM сбор данных (unchanged)
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

        # ✅ ФИКС: Передаем timeout_callback напрямую
        timer = TestTimer(callback.bot, callback.message.chat.id, callback.from_user.id, difficulty)
        await timer.start(timeout_callback)  # ← Аргумент!

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

@oupds_router.callback_query(F.data.startswith("toggle_"))
async def toggle_answer(callback: CallbackQuery, state: FSMContext):
    """✅ Множественный выбор: toggle + клавиатура (варианты с галочками + Далее)."""
    user_id = callback.from_user.id
    test_state = oupds_TEST_STATES.get(user_id)
    if not test_state:
        return await callback.answer("❌ Сессия истекла")

    # ✅ Toggle логика (добавляем/убираем из selected_answers)
    await handle_answer_toggle(callback, test_state)

    # ✅ Строим клавиатуру: варианты + галочки + Далее внизу
    q = test_state.questions[test_state.current_question_idx]
    markup = get_test_keyboard(q.options, test_state.selected_answers or set())
    
    # Добавляем «Далее» отдельной строкой (НЕ заменяем варианты!)
    markup.inline_keyboard.append([InlineKeyboardButton(text="➡️ Далее", callback_data="next")])

    # ✅ ТОЛЬКО клавиатуру обновляем (вопрос на месте!)
    await callback.message.edit_reply_markup(reply_markup=markup)
    await callback.answer("✓ Отмечено" if callback.data.split("_")[1] in test_state.selected_answers else "✗ Снято")
    logger.info(f"Toggle {user_id}: {sorted(test_state.selected_answers)}")

@oupds_router.callback_query(F.data == "next")
async def next_question_handler(callback: CallbackQuery, state: FSMContext):
    """✅ Delete ТОЛЬКО здесь + следующий вопрос."""
    user_id = callback.from_user.id
    test_state = oupds_TEST_STATES.get(user_id)
    if not test_state:
        return await callback.answer("❌ Сессия истекла")

    # ✅ Сохраняем ответы этого вопроса
    if test_state.selected_answers:
        test_state.answers_history.append(test_state.selected_answers.copy())
    test_state.selected_answers = set()

    # ✅ Удаляем ТЕКУЩИЙ вопрос
    await callback.message.delete()

    # ✅ FSM данные для user_data
    data = await state.get_data()
    user_data = UserData(**data, difficulty=test_state.questions[0].difficulty)

    # ✅ handle_next_question: следующий или finish
    await handle_next_question(callback, test_state, user_data)
    logger.info(f"✅ Next {user_id} (история: {len(test_state.answers_history)})")
    await callback.answer()

@oupds_router.callback_query(F.data == "finish_test")
async def finish_test_handler(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    test_state = oupds_TEST_STATES.get(user_id)
    if not test_state:
        return await callback.answer("❌ Сессия истекла")

    try:
        await callback.message.delete()
        data = await state.get_data()
        user_data = UserData(**data, difficulty=test_state.questions[0].difficulty if test_state.questions else Difficulty.BASIC)
        results = calculate_test_results(test_state)  # ✅ Вызов
        await finish_test(callback.message, test_state, user_data, results)
        
        oupds_TEST_STATES.pop(user_id, None)
        await state.clear()
        logger.info(f"✅ Завершён {user_id}")
    except Exception as e:
        logger.error(f"Finish error: {e}")
        await callback.answer("❌ Завершение")
    await callback.answer()
