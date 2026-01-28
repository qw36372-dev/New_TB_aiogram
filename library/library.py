"""
Core library: функции теста (toggle, next, finish).
Для импорта в specializations/*.py.
Production: delete messages, stats, PDF stub, fallbacks.
"""
import asyncio
import logging
from typing import Optional
from aiogram.types import CallbackQuery, Message, FSInputFile
from aiogram.fsm.context import FSMContext

from config.settings import settings
from .models import CurrentTestState
from . import safe_timer_remaining, safe_timer_stop, get_test_keyboard, get_finish_keyboard
from .timers import TestTimer  # Предполагаем следующий файл

logger = logging.getLogger(__name__)

async def _show_question(
    question_obj: 'Question', 
    test_state: CurrentTestState, 
    message: Message | CallbackQuery
) -> None:
    """Показ вопроса: нумер текст, ⏰, клавиатура."""
    msg = message if isinstance(message, Message) else message.message
    
    # ⏰ + вопрос 1/20
    time_left = safe_timer_remaining(test_state.timer_task)
    header = f"⏰ {time_left}\n\nВопрос {test_state.current_index + 1}/{len(test_state.questions)}:"
    full_text = f"{header}\n\n{question_obj.question}"
    
    keyboard = get_test_keyboard(question_obj.options, test_state.selected_answers)
    await msg.edit_text(full_text, reply_markup=keyboard)

async def handle_answer_toggle(
    callback: CallbackQuery, 
    test_state: CurrentTestState
) -> None:
    """Toggle ответ: add/remove set + edit markup (вопрос stays)."""
    try:
        ans_idx = int(callback.data.split("_")[1])
        if ans_idx in test_state.selected_answers:
            test_state.selected_answers.discard(ans_idx)
        else:
            test_state.selected_answers.add(ans_idx)
        
        question = test_state.questions[test_state.current_index]
        await _show_question(question, test_state, callback)
        logger.info(f"Toggle {callback.from_user.id}: {ans_idx} in {test_state.specialization}")
    except (ValueError, IndexError) as e:
        logger.error(f"Toggle error: {e}")
        await callback.answer("❌ Ошибка выбора")
    await callback.answer()

async def handle_next_question(
    callback: CallbackQuery, 
    test_state: CurrentTestState, 
    user_data: dict
) -> None:
    """➡️ Далее: delete + следующий вопрос или finish."""
    await callback.message.delete()
    
    test_state.current_index += 1
    if test_state.current_index >= len(test_state.questions):
        await finish_test(callback.message, test_state)
        return
    
    question = test_state.questions[test_state.current_index]
    await _show_question(question, test_state, callback.message)
    await user_data.update(test_state=test_state)  # FSM persist
    logger.info(f"Next {callback.from_user.id}: {test_state.current_index}")

async def finish_test(
    message: Message, 
    test_state: CurrentTestState
) -> None:
    """Завершить: stats, stop timer, PDF stub, finish keyboard."""
    safe_timer_stop(test_state.timer_task)
    
    total = len(test_state.questions)
    correct = 0
    for q in test_state.questions:
        if test_state.selected_answers & q.correct_answers:  # Multiple OK if intersect
            correct += 1
    
    score = (correct / total) * 100
    stats_text = (
        f"✅ Завершен тест: {test_state.specialization} ({test_state.difficulty.value})\n"
        f"👤 {test_state.full_name}, {test_state.position}\n"
        f"📊 Правильно: {correct}/{total} ({score:.1f}%)\n\n"
        f"Генерация сертификата..."
    )
    
    # PDF stub (ReportLab next)
    pdf_path = settings.work_dir / settings.certs_dir / f"{test_state.specialization}_{message.from_user.id}.pdf"
    # await generate_pdf(test_state, pdf_path)  # Stub
    
    keyboard = get_finish_keyboard()
    await message.answer(stats_text, reply_markup=keyboard)
    logger.info(f"Finish {message.from_user.id}: {score:.1f}% {test_state.specialization}")
