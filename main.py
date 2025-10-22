# main.py
import logging
import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, SUPER_ADMIN_IDS, RECEIPTS_FOLDER, LOGGING_CONFIG
from handlers import register_handlers
from database import Database

# Настройка логирования
logging.basicConfig(**LOGGING_CONFIG)
logger = logging.getLogger(__name__)

async def main():
    try:
        # Создаем папку для чеков
        if not os.path.exists(RECEIPTS_FOLDER):
            os.makedirs(RECEIPTS_FOLDER)
            logger.info(f"Создана папка для чеков: {RECEIPTS_FOLDER}")

        # Инициализация
        logger.info("Инициализация бота...")
        storage = MemoryStorage()
        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher(storage=storage)

        # Инициализация базы данных
        logger.info("Инициализация базы данных...")
        db = Database()

        # Регистрация обработчиков
        logger.info("Регистрация обработчиков...")
        register_handlers(dp, db, bot)

        # Запуск бота
        logger.info("BAD Exchanger бот запущен...")
        print("=" * 50)
        print("🎯 BAD Exchanger - Бот успешно запущен!")
        print(f"👑 Супер-админы: {SUPER_ADMIN_IDS}")
        print("=" * 50)

        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        print(f"❌ Критическая ошибка: {e}")
        raise

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Непредвиденная ошибка: {e}")