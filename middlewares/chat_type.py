from typing import Callable, Awaitable, Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery


class PrivateChatOnlyMiddleware(BaseMiddleware):
    """
    In private chats: allows all messages.
    In groups/supergroups: only allows when bot is explicitly commanded,
    tagged (@bot_username), or replied to, preventing unwanted chat spam.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict], Awaitable[Any]],
        event: TelegramObject,
        data: dict,
    ) -> Any:
        if isinstance(event, Message):
            if event.chat.type in ("group", "supergroup"):
                bot = data.get("bot")
                bot_info = await bot.get_me() if bot else None
                bot_username = (bot_info.username or "").lower() if bot_info else ""
                text = (event.text or event.caption or "").strip()

                is_reply_to_bot = bool(
                    event.reply_to_message
                    and event.reply_to_message.from_user
                    and bot_info
                    and event.reply_to_message.from_user.id == bot_info.id
                )
                is_command = text.startswith("/")
                mentions_bot = bool(
                    (bot_username and f"@{bot_username}" in text.lower())
                    or any(
                        e.type == "text_mention" and bot_info and e.user and e.user.id == bot_info.id
                        for e in (event.entities or [])
                    )
                    or any(
                        e.type == "mention" and bot_username and text[e.offset:e.offset + e.length].lower() == f"@{bot_username}"
                        for e in (event.entities or [])
                    )
                )

                # If not commanded and not mentioned and not replied to bot, ignore
                if not (is_command or mentions_bot or is_reply_to_bot):
                    return
        elif isinstance(event, CallbackQuery):
            pass

        return await handler(event, data)
