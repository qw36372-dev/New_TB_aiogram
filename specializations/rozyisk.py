"""
Роутер специализации "Алименты" — полный тест с FSM.
Шаблон для остальных 10 (скопируйте, замените "rozyisk" и название кнопки).
ФИНАЛЬНАЯ РАБОЧАЯ ВЕРСИЯ для production на Bothost.ru.
"""
import asyncio
import logging
import os
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

rozyisk_router = Router()
rozyisk_router.message.middleware(AntiSpamMiddleware())

async def timeout_callback(bot, chat_id: int, user_id: int):
    """Обработчик таймаута теста."""
    await bot.send_message(
        chat_id, 
        "⏰ <b>Время вышло!</b>\n\nТест не сдан. Выберите /start для нового.",
        parse_mode="HTML"
    )
    if user_id in TEST_STATES:
        del TEST_STATES[user_id]

@rozyisk_router.message(F.text == "Алименты")
async def start_rozyisk_test(message: Message, state: FSMContext):
    """Начало теста по Алиментам."""
    await message.delete()
    await message.bot.send_message(
        message.chat.id, 
        get_logo_text(), 
        reply_markup=get_main_keyboard()
    )
    await state.set_state(TestStates.waiting_full_name)
    await message.answer("📝 Введите ФИО:")

@rozyisk_router.message(StateFilter(TestStates.waiting_full_name))
async def process_full_name(message: Message, state: FSMContext):
    """Сохранение ФИО."""
    await state.update_data(full_name=message.text.strip())
    await message.delete()
    await state.set_state(TestStates.waiting_position)
    await message.answer("💼 Должность:")

@rozyisk_router.message(StateFilter(TestStates.waiting_position))
async def process_position(message: Message, state: FSMContext):
    """Сохранение должности."""
    await state.update_data(position=message.text.strip())
    await message.delete()
    await state.set_state(TestStates.waiting_department)
    await message.answer("🏢 Подразделение:")

@rozyisk_router.message(StateFilter(TestStates.waiting_department))
async def process_department(message: Message, state: FSMContext):
    """Переход к выбору сложности."""
    data = await state.get_data()
    data["department"] = message.text.strip()
    data["specialization"] = "rozyisk"
    await message.delete()
    await state.update_data(**data)
    await state.set_state(TestStates.answering_question)
    await message.answer(
        "⚙️ Выберите уровень сложности:", 
        reply_markup=get_difficulty_keyboard()
    )

@rozyisk_router.callback_query(F.data.startswith("diff_"))
async def select_difficulty(callback: CallbackQuery, state: FSMContext):
    """Инициализация теста по сложности."""
    _, diff_name = callback.data.split("_", 1)
    difficulty = Difficulty(diff_name)
    
    data = await state.get_data()
    user_data = UserData(
        **data, 
        difficulty=difficulty
    )
    await state.update_data(user_data=user_data.model_dump())
    
    # Загрузка вопросов из JSON
    questions = load_questions_for_specialization(
        user_data.specialization, difficulty, callback.from_user.id
    )
    
    # Таймер
    timer = TestTimer(callback.bot, callback.message.chat.id, callback.from_user.id, difficulty)
    await timer.start(lambda: asyncio.create_task(
        timeout_callback(callback.bot, callback.message.chat.id, callback.from_user.id)
    ))
    
    # Состояние теста с историей ответов
    test_state = CurrentTestState(
        callback.from_user.id, questions, timer=timer, answers_history=[]
    )
    TEST_STATES[callback.from_user.id] = test_state
    
    await callback.message.delete()
    await callback.message.answer("🚀 <b>Тест начат!</b>", parse_mode="HTML")
    await start_question(callback.message, state)
    await callback.answer()

async def start_question(message: Message, state: FSMContext):
    """Отображение текущего вопроса."""
    user_id = message.from_user.id
    test_state = TEST_STATES[user_id]
    
    if test_state.current_question_idx >= len(test_state.questions):
        await finish_test(message, state)
        return
    
    q = test_state.questions[test_state.current_question_idx]
    time_left = test_state.timer.remaining_time()
    
    options_text = "\n".join([f"{i}. {opt}" for i, opt in enumerate(q.options, 1)])
    
    await message.answer(
        f"⏰ <b>{time_left}</b>\n\n"
        f"❓ <b>Вопрос {test_state.current_question_idx + 1}:</b>\n"
        f"{q.question}\n\n"
        f"{options_text}",
        reply_markup=get_test_keyboard(test_state.selected_answers or set()),
        parse_mode="HTML"
    )

@rozyisk_router.callback_query(F.data.startswith("ans_"))
async def toggle_answer(callback: CallbackQuery, state: FSMContext):
    """Переключение выбора ответа."""
    _, idx_str = callback.data.split("_")
    idx = int(idx_str)
    
    user_id = callback.from_user.id
    test_state = TEST_STATES[user_id]
    
    if test_state.selected_answers is None:
        test_state.selected_answers = set()
    
    if idx in test_state.selected_answers:
        test_state.selected_answers.discard(idx)
    else:
        test_state.selected_answers.add(idx)
    
    await callback.message.edit_reply_markup(
        reply_markup=get_test_keyboard(test_state.selected_answers)
    )
    await callback.answer()

@rozyisk_router.callback_query(F.data == "next_question")
async def next_question(callback: CallbackQuery, state: FSMContext):
    """Переход к следующему вопросу."""
    user_id = callback.from_user.id
    test_state = TEST_STATES[user_id]
    
    # Сохраняем ответы текущего вопроса
    test_state.answers_history.append(test_state.selected_answers or set())
    test_state.current_question_idx += 1
    test_state.selected_answers = None
    
    await callback.message.delete()
    await start_question(callback.message, state)
    await callback.answer()

async def finish_test(message: Message, state: FSMContext):
    """Завершение теста: подсчёт, сохранение, PDF."""
    user_id = message.from_user.id
    test_state = TEST_STATES[user_id]
    elapsed = await test_state.timer.stop()
    
    data = await state.get_data()
    user_data = UserData(**data["user_data"])
    
    # Подсчёт правильных ответов по истории
    correct = 0
    total_questions = len(test_state.questions)
    for i, q in enumerate(test_state.questions):
        if test_state.answers_history[i] == q.correct_answers:
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
    
    # Удаление временного PDF (асинхронно)
    asyncio.create_task(asyncio.to_thread(os.remove, cert_path))
