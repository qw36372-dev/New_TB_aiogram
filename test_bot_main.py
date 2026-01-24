#!/usr/bin/env python3
"""
test_bot_main.py — Production-ready Aiogram 3.x Telegram тест-бот для Bothost.ru!
11 специализаций × FSM × PDF × AntiSpam. MemoryStorage. Graceful shutdown.
"""

import asyncio
import importlib
import logging
import os
import sys
import signal
from pathlib import Path
from typing import List

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

try:
    from config.settings import Settings
except ImportError as e:
    raise ImportError("config.settings не найден. Создайте файл с class Settings и api_token = os.getenv('API_TOKEN')") from e

# ✅ Исправленный импорт через __init__.py
try:
    from library import AntiSpamMiddleware
except ImportError as e:
    raise ImportError("library.AntiSpamMiddleware не найден. Создайте middleware в library или удалите строку.") from e

# Список роутеров для динамической загрузки
SPECIALIZATIONS = [
    "oupds", "ispolniteli", "aliment", "doznanie", "rozyisk",
    "prof", "oko", "informatika", "kadry", "bezopasnost", "upravlenie"
]

# Настройка логирования
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/bot.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Глобальные переменные
bot: Bot | None = None
dp: Dispatcher | None = None

def load_router(module_name: str) -> bool:
    """Загрузка роутера с проверкой через importlib."""
    try:
        spec_module = importlib.import_module(f"specializations.{module_name}")
        if not hasattr(spec_module, f"{module_name}_router"):
            raise AttributeError(f"Роутер {module_name}_router не найден")
        router = getattr(spec_module, f"{module_name}_router")
        dp.include_router(router)
        logger.info(f"✅ Загружен роутер: {module_name}_router")
        return True
    except (ImportError, AttributeError) as e:
        logger.error(f"✗ Ошибка загрузки {module_name}: {e}")
        return False

async def on_startup():
    logger.info("🚀 Бот инициализирован и готов к работе")

async def on_shutdown():
    logger.info("🛑 Завершение работы бота")
    # Graceful shutdown задач
    if dp:
        tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    if bot:
        await bot.session.close()
    logger.info("👋 Бот остановлен корректно")

async def main():
    global bot, dp
    
    # Инициализация
    settings = Settings()
    if not settings.api_token:
        logger.error("API_TOKEN отсутствует")
        sys.exit(1)
    
    bot = Bot(token=settings.api_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # ✅ Middleware ПЕРЕД роутерами
    try:
        dp.message.middleware(AntiSpamMiddleware())
        logger.info("✅ AntiSpamMiddleware подключен")
    except Exception as e:
        logger.warning(f"Middleware warning: {e}")
    
    # === ROOT РОУТЕР /start ТОЛЬКО ===
    main_router = Router()
    
    @main_router.message(Command("start"))
    async def cmd_start(message: Message):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚨 ООУПДС", callback_data="oupds")],
            [InlineKeyboardButton(text="📊 Исполнители", callback_data="ispolniteli")],
            [InlineKeyboardButton(text="💰 Алименты", callback_data="aliment")],
            [InlineKeyboardButton(text="🎯 Дознание", callback_data="doznanie")],
            [InlineKeyboardButton(text="🔍 Розыск", callback_data="rozyisk")],
            [InlineKeyboardButton(text="📚 Профстандарты", callback_data="prof")],
            [InlineKeyboardButton(text="👁️ ОКО", callback_data="oko")],
            [InlineKeyboardButton(text="💻 Информатизация", callback_data="informatika")],
            [InlineKeyboardButton(text="👥 Кадры", callback_data="kadry")],
            [InlineKeyboardButton(text="🛡️ Безопасность", callback_data="bezopasnost")],
            [InlineKeyboardButton(text="🏛️ Управление", callback_data="upravlenie")]
        ])
        await message.answer("🧪 ФССП Тест-бот\nВыберите специализацию:", reply_markup=kb)
    
    dp.include_router(main_router)
    
    # === 11 СПЕЦИАЛИЗАЦИЙ ===
    loaded_count = 0
    for spec in SPECIALIZATIONS:
        if load_router(spec):
            loaded_count += 1
    
    logger.info(f"🚀 Загружено роутеров: {loaded_count}/{len(SPECIALIZATIONS)}")
    logger.info("Запуск polling...")
    
    # ✅ Улучшенные signals (loop-aware)
    loop = asyncio.get_running_loop()
    def signal_handler(signum, frame):
        logger.info(f"Сигнал {signum}")
        if dp:
            loop.call_soon_threadsafe(dp.stop_polling)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Polling с обработкой ошибок
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt")
    except Exception as e:
        logger.error(f"Polling error: {e}", exc_info=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Прервано пользователем")
    except Exception as e:
        logger.error(f"Фатальная ошибка: {e}", exc_info=True)
        sys.exit(1)
