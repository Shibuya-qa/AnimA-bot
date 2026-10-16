from typing import Callable, Awaitable, Any
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from database.db import get_sub_channels as get_channels
from config import ADMIN_IDS
from database.db import is_admin_in_db


async def check_subscription(bot, user_id: int, channels: list) -> list:
    """Returns list of channels user is NOT subscribed to."""
    not_subscribed = []
    for ch in channels:
        try:
            member = await bot.get_chat_member(ch["channel_id"], user_id)
            if member.status in ("left", "kicked", "banned"):
                not_subscribed.append(ch)
        except Exception:
            not_subscribed.append(ch)
    return not_subscribed


def subscribe_keyboard(not_subscribed: list) -> Any:
    builder = InlineKeyboardBuilder()
    for ch in not_subscribed:
        builder.row(InlineKeyboardButton(
            text=f"📢 {ch['channel_name']}",
            url=ch["channel_link"]
        ))
    builder.row(InlineKeyboardButton(
        text="✅ Tekshirish",
        callback_data="check_subscription"
    ))
    return builder.as_markup()


class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict], Awaitable[Any]],
        event: TelegramObject,
        data: dict,
    ) -> Any:
        bot = data["bot"]

        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            # always allow subscription check callback
            if event.data == "check_subscription":
                return await handler(event, data)
            user_id = event.from_user.id
        else:
            return await handler(event, data)

        # admins bypass subscription check
        if user_id in ADMIN_IDS or await is_admin_in_db(user_id):
            return await handler(event, data)

        channels = await get_channels()
        if not channels:
            return await handler(event, data)

        not_subscribed = await check_subscription(bot, user_id, channels)
        if not not_subscribed:
            return await handler(event, data)

        user = event.from_user
        mention = f"@{user.username}" if user.username else f"<a href='tg://user?id={user.id}'>{user.full_name}</a>"
        text = (
            f"⚠️ <b>{mention}</b>, botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:\n\n"
            + "\n".join(f"• {ch['channel_name']}" for ch in not_subscribed)
        )
        kb = subscribe_keyboard(not_subscribed)

        if isinstance(event, Message):
            await event.answer(text, parse_mode="HTML", reply_markup=kb)
        elif isinstance(event, CallbackQuery):
            await event.answer("⚠️ Avval kanallarga obuna bo'ling!", show_alert=True)
            await event.message.answer(text, parse_mode="HTML", reply_markup=kb)
        return
