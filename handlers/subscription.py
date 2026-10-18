from aiogram import Router, F
from aiogram.types import CallbackQuery

from database.db import get_sub_channels as get_channels
from middlewares.subscription import check_subscription, subscribe_keyboard
from keyboards.main import main_menu

router = Router()


@router.callback_query(F.data == "check_subscription")
async def check_sub_handler(callback: CallbackQuery):
    channels = await get_channels()
    not_subscribed = await check_subscription(callback.bot, callback.from_user.id, channels)

    if not_subscribed:
        text = (
            "❌ <b>Siz hali quyidagi kanallarga obuna bo'lmadingiz:</b>\n\n"
            + "\n".join(f"• {ch['channel_name']}" for ch in not_subscribed)
        )
        await callback.message.edit_text(
            text, parse_mode="HTML",
            reply_markup=subscribe_keyboard(not_subscribed)
        )
        await callback.answer("❌ Hali obuna bo'lmadingiz!", show_alert=True)
    else:
        await callback.message.delete()
        if callback.message.chat.type in ("group", "supergroup"):
            await callback.message.answer(
                "✅ <b>Rahmat! Endi guruhda botdan foydalanishingiz mumkin.</b>",
                parse_mode="HTML"
            )
        else:
            await callback.message.answer(
                "✅ <b>Rahmat! Endi botdan foydalanishingiz mumkin.</b>",
                parse_mode="HTML",
                reply_markup=main_menu()
            )
        await callback.answer("✅ Tabriklaymiz!")
