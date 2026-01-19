#!/usr/bin/env python3
"""
test_bot_main.py — Production-ready Aiogram 3.x Telegram тест-бот для Bothost.ru!
11 специализаций × FSM × PDF × AntiSpam. MemoryStorage. Graceful shutdown.
"""

import asyncio
import logging
import os
import sys
import signal
from pathlib import Path
from typing import List

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command

try:
    from config.settings import Settings
except ImportError as e:
    raise ImportError("config.settings не найден. Создайте файл с class Settings и api_token = os.getenv('API_TOKEN')") from e

try:
    from library.anti_spam import AntiSpamMiddleware
except ImportError as e:
    raise ImportError("library.anti_spam не найден. Создайте middleware или удалите строку.") from e

# Список роутеров для динамической загрузки с проверкой
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

# Глобальные переменные для shutdown
bot: Bot | None = None
dp: Dispatcher | None = None

def load_router(module_name: str) -> bool:
    """Загрузка роутера с проверкой."""
    try:
        mod = __import__(f"specializations.{module_name}", fromlist=["router"])
        router = getattr(mod, f"{module_name}_router")
        dp.include_router(router)  # Упрощено: dp всегда готов
        logger.info(f"✅ Загружен роутер: {module_name}_router")
        return True
    except (ImportError, AttributeError) as e:
        logger.error(f"✗ Ошибка загрузки {module_name}: {e}")
    return False

async def on_startup():
    """Startup hook."""
    logger.info("🚀 Бот инициализирован и готов к работе")

async def on_shutdown():
    """Shutdown hook."""
    logger.info("🛑 Завершение работы бота")
    if bot:
        await bot.session.close()
    logger.info("👋 Бот остановлен корректно")

async def main():
    """Главная функция запуска бота."""
    global bot, dp
    
    # Инициализация настроек с проверкой
    try:
        settings = Settings()
    except Exception as e:
        logger.error(f"Ошибка настроек: {e}")
        sys.exit(1)
    
    # Проверка токена
    if not settings.api_token:
        logger.error("API_TOKEN отсутствует в окружении")
        sys.exit(1)
    
    # Инициализация бота
    bot = Bot(
        token=settings.api_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Dispatcher с MemoryStorage (данные в RAM, сбрасываются при рестарте)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Startup/Shutdown hooks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Подключение middleware с обработкой ошибок
    try:
        dp.message.middleware(AntiSpamMiddleware())
        logger.info("✅ AntiSpamMiddleware подключен")
    except Exception as e:
        logger.warning(f"Предупреждение middleware: {e}")
    
    # Динамическая загрузка роутеров
    loaded_count = 0
    for spec in SPECIALIZATIONS:
        if load_router(spec):
            loaded_count += 1
    
    logger.info(f"🚀 Загружено роутеров: {loaded_count}/{len(SPECIALIZATIONS)}")
    
    if loaded_count == 0:
        logger.warning("Нет загруженных модулей специализаций!")
    
    logger.info("Бот запущен в polling режиме (MemoryStorage)")
    
    # Graceful shutdown signals
    def signal_handler(signum, frame):
        logger.info(f"Получен сигнал {signum}, завершение...")
        asyncio.create_task(dp.stop_polling())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

# Главный роутер меню
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

    # Запуск polling с обработкой ошибок
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Получен KeyboardInterrupt")
    except Exception as e:
        logger.error(f"Критическая ошибка polling: {e}", exc_info=True)
    finally:
        await bot.session.close()
        logger.info("Бот остановлен корректно")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Программа прервана пользователем")
    except Exception as e:
        logger.error(f"Фатальная ошибка: {e}", exc_info=True)
        sys.exit(1)
