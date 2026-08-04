from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from database.db import get_user_history, get_favorites
from keyboards.main import cabinet_menu, main_menu

router = Router()


@router.message(F.text == "🗂 Kabinet")
async def cabinet_handler(message: Message):
    text = (
        f"🗂 <b>Kabinet</b>\n\n"
        f"👤 <b>{message.from_user.full_name}</b>\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n"
        f"🔗 Username: @{message.from_user.username or 'yo\'q'}\n\n"
        f"Nima ko'rishni xohlaysiz?"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=cabinet_menu())


@router.callback_query(F.data == "cabinet:history")
async def history_handler(callback: CallbackQuery):
    history = await get_user_history(callback.from_user.id)
    if not history:
        await callback.answer("📜 Ko'rish tarixi bo'sh", show_alert=True)
        return

    lines = ["📜 <b>So'nggi ko'rilgan animeler:</b>\n"]
    for i, item in enumerate(history, 1):
        lines.append(f"{i}. <b>{item['name']}</b> — <code>{item['code']}</code>")

    await callback.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=cabinet_menu())


@router.callback_query(F.data == "cabinet:favorites")
async def favorites_handler(callback: CallbackQuery):
    favs = await get_favorites(callback.from_user.id)
    if not favs:
        await callback.answer("❤️ Sevimlilar bo'sh", show_alert=True)
        return

    lines = ["❤️ <b>Sevimli animelerim:</b>\n"]
    for i, item in enumerate(favs, 1):
        lines.append(f"{i}. <b>{item['name']}</b> — <code>{item['code']}</code>")

    await callback.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=cabinet_menu())


@router.callback_query(F.data == "cabinet:back")
async def cabinet_back(callback: CallbackQuery):
    await callback.message.delete()


@router.callback_query(F.data == "cabinet:guide")
async def guide_handler(callback: CallbackQuery):
    text = (
        "📖 <b>Qo'llanma</b>\n\n"
        "1️⃣ Anime kodini yozing (masalan: <code>AOT01</code>)\n"
        "2️⃣ Bot sizga animeni ma'lumotlari bilan birga yuboradi\n"
        "3️⃣ <b>Yuklab olish</b> tugmasini bosib faylni oling\n\n"
        "📌 Kodlarni kanalimizdan topishingiz mumkin!"
    )
    from keyboards.main import cabinet_menu
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=cabinet_menu())


@router.callback_query(F.data == "cabinet:reklama")
async def reklama_handler(callback: CallbackQuery):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    text = (
        "📢 <b>Reklama berish</b>\n\n"
        "Reklamani joylashtirish uchun quyidagi manzilga murojaat qiling:\n"
        "👤 @Shoxrux_Daminov"
    )
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="👤 @Shoxrux_Daminov", url="https://t.me/Shoxrux_Daminov"))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="cabinet:back"))
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())
