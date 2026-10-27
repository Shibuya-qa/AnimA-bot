import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
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
    try:
        from sync_webapp import sync_animes
        sync_animes()
    except Exception as e:
        logging.warning(f"Webapp ma'lumotlarini sinxronlashda xatolik: {e}")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode="HTML",
            protect_content=True
        )
    )
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

    from utils.backup import daily_backup_scheduler
    asyncio.create_task(daily_backup_scheduler(bot))

    # ShoDa Mini App veb-serverini ishga tushirish
    try:
        from server import run_server
        asyncio.create_task(run_server(host="0.0.0.0", port=8080))
    except Exception as e:
        logging.warning(f"Mini App serverini ishga tushirishda xatolik: {e}")

    logging.info("Bot ishga tushdi!")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
