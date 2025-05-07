import asyncio
from aiogram import Bot
from aiogram import Dispatcher
from config.configurations import load_config

from aiogram.fsm.storage.memory import MemoryStorage
from handlers.main_handlers import router as main_router
from handlers.content_callbacks import router as content_router
from handlers.activity_timer import activity_timer
from handlers.interactive import interactive_router
from llm.worker import llm_worker

import logging


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def main():
    config = load_config()

    bot: Bot = Bot(token=config.tg_bot.token)
    dp: Dispatcher = Dispatcher(storage=MemoryStorage())

    dp.include_routers(main_router, interactive_router, content_router)

    llm_worker.start()

    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("запуск бота..")
    try:
        await dp.start_polling(bot)
    finally:
        logger.info("остановка бота...")
        llm_worker.stop()
        logger.info("бот остановлен")


if __name__ == "__main__":
    asyncio.run(main())
