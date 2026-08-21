from typing import Callable, Awaitable, Any
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from database.db import touch_user_activity


class ActivityMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict], Awaitable[Any]],
        event: TelegramObject,
        data: dict,
    ) -> Any:
        user = None
        if isinstance(event, Message) and event.from_user:
            user = event.from_user
        elif isinstance(event, CallbackQuery) and event.from_user:
            user = event.from_user

        if user:
            try:
                await touch_user_activity(
                    user_id=user.id,
                    username=user.username or "",
                    full_name=user.full_name or ""
                )
            except Exception:
                pass

        return await handler(event, data)
