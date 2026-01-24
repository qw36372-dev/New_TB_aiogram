"""
Общие клавиатуры: главное меню, уровни сложности, тест, результаты.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from .models import Difficulty
from config.settings import settings

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню: 11 специализаций + Помощь."""
    builder = ReplyKeyboardBuilder()
    
    # 11 кнопок специализаций
    specs = [
        "🚨 ООУПДС", 
        "📊 Исполнительное производство", 
        "🧑‍🧑‍🧒 Алименты",
        "🎯 Дознание", 
        "⏳ Исполнительный розыск и реализация имущества",
        "📈 Организация профессиональной подготовки",
        "📡 Организация управления и контроля",
        "📱 Информатизация и информационная безопасность",
        "💻 Кадровая работа",
        "🔒 Обеспечение собственной безопасности", 
        "💼 Управленческая деятельность"
    ]
    
    for spec in specs:
        builder.button(text=spec)
    builder.button(text="❓ Помощь 🆘")
    builder.adjust(2, 2)  # 2 колонки
    
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)

def get_difficulty_keyboard() -> InlineKeyboardMarkup:
    """Выбор уровня сложности."""
    builder = InlineKeyboardBuilder()
    for diff in Difficulty:
        builder.button(text=diff.value.capitalize(), callback_data=f"diff_{diff.value}")
    builder.adjust(1)
    return builder.as_markup()

def get_test_keyboard(options: list[str], selected: set[int] | None = None) -> InlineKeyboardMarkup:
    """Клавиатура теста: динамические опции вопроса + toggle + Далее."""
    builder = InlineKeyboardBuilder()
    selected = selected or set()
    
    for i, opt_text in enumerate(options):  # Динамика: реальные тексты из q.options
        state = "✅" if i in selected else "⬜"
        builder.button(
            text=f"{state} {opt_text}",
            callback_data=f"toggle_{i}"  # Совместимо с handle_answer_toggle
        )
    
    builder.button(text="➡️ Далее", callback_data="next").adjust(1)
    builder.adjust(2)
    return builder.as_markup()

def get_finish_keyboard() -> InlineKeyboardMarkup:
    """После теста: показать ответы, сертификат, повторить, статистика."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Показать правильные ответы", callback_data="show_answers")
    builder.button(text="🏆 Сертификат PDF", callback_data="generate_cert")
    builder.button(text="🔄 Повторить тест", callback_data="repeat_test")
    builder.button(text="📊 Моя статистика", callback_data="my_stats")
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    builder.adjust(2)
    return builder.as_markup()
