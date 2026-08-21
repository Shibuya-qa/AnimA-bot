import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database.db import init_db
from handlers import start, anime, cabinet, admin, subscription, channel
from middlewares.subscription import SubscriptionMiddleware
from middlewares.chat_type import PrivateChatOnlyMiddleware
from middlewares.activity import ActivityMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


async def main():
    await init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(PrivateChatOnlyMiddleware())
    dp.callback_query.middleware(PrivateChatOnlyMiddleware())
    dp.message.middleware(ActivityMiddleware())
    dp.callback_query.middleware(ActivityMiddleware())
    dp.message.middleware(SubscriptionMiddleware())
    dp.callback_query.middleware(SubscriptionMiddleware())

    dp.include_router(subscription.router)
    dp.include_router(start.router)
    dp.include_router(cabinet.router)
    dp.include_router(admin.router)
    dp.include_router(channel.router)
    dp.include_router(anime.router)

    logging.info("Bot ishga tushdi!")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
