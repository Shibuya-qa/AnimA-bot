from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.db import get_user_history, get_favorites
from keyboards.main import cabinet_menu

router = Router()


@router.message(F.text == "🗂 Kabinet")
async def cabinet_handler(message: Message):
    text = (
        f"🗂 <b>Foydalanuvchi Kabineti</b>\n\n"
        f"👤 <b>{message.from_user.full_name}</b>\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n"
        f"🔗 Username: @{message.from_user.username or 'yo\'q'}\n\n"
        f"✨ Kerakli bo'limni tanlang:"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=cabinet_menu())


@router.callback_query(F.data == "cabinet:history")
async def history_handler(callback: CallbackQuery):
    history = await get_user_history(callback.from_user.id)
    if not history:
        await callback.answer("📜 Ko'rish tarixi bo'sh", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for item in history:
        builder.row(InlineKeyboardButton(
            text=f"🎬 {item['name']} [{item['code']}]",
            callback_data=f"catalog:view:{item['anime_id']}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Kabinetga qaytish", callback_data="cabinet:back"))

    await callback.message.edit_text(
        "📜 <b>So'nggi ko'rilgan animelar:</b>\n\nTomosha qilish uchun tanlang:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data == "cabinet:favorites")
async def favorites_handler(callback: CallbackQuery):
    favs = await get_favorites(callback.from_user.id)
    if not favs:
        await callback.answer("❤️ Sevimlilar ro'yxati bo'sh", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for item in favs:
        builder.row(InlineKeyboardButton(
            text=f"❤️ {item['name']} [{item['code']}]",
            callback_data=f"catalog:view:{item['anime_id']}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Kabinetga qaytish", callback_data="cabinet:back"))

    await callback.message.edit_text(
        "❤️ <b>Sevimli animelaringiz:</b>\n\nTomosha qilish uchun tanlang:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data == "cabinet:back")
async def cabinet_back(callback: CallbackQuery):
    username = callback.from_user.username or "yo'q"
    text = (
        f"🗂 <b>Foydalanuvchi Kabineti</b>\n\n"
        f"👤 <b>{callback.from_user.full_name}</b>\n"
        f"🆔 ID: <code>{callback.from_user.id}</code>\n"
        f"🔗 Username: @{username}\n\n"
        f"✨ Kerakli bo'limni tanlang:"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=cabinet_menu())


@router.callback_query(F.data == "cabinet:guide")
async def guide_handler(callback: CallbackQuery):
    text = (
        "📖 <b>Botdan foydalanish qo'llanmasi</b>\n\n"
        "1️⃣ <b>Qidirish:</b> Anime nomini (masalan: <code>Naruto</code>) yoki kodini (masalan: <code>81</code>) yuboring.\n"
        "2️⃣ <b>Top Animelar:</b> Eng ko'p ko'rilgan va mashhur animelarni topishingiz mumkin.\n"
        "3️⃣ <b>Janrlar:</b> O'zingiz yoqtirgan janr bo'yicha saralang.\n"
        "4️⃣ <b>Inline qidiruv:</b> Istalgan guruh yoki chatda <code>@animafundubbot anime_nomi</code> deb qidirishingiz mumkin.\n"
        "5️⃣ <b>Baholash:</b> Ko'rgan animeingizga ⭐ baho berishni unutmang!"
    )
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Kabinetga qaytish", callback_data="cabinet:back"))
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())


@router.callback_query(F.data == "cabinet:reklama")
async def reklama_handler(callback: CallbackQuery):
    text = (
        "📢 <b>Reklama va Hamkorlik</b>\n\n"
        "Botda reklama joylashtirish yoki hamkorlik bo'yicha murojaat:\n"
        "👤 @Shoxrux_Daminov"
    )
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💬 Aloqaga chiqish", url="https://t.me/Shoxrux_Daminov"))
    builder.row(InlineKeyboardButton(text="🔙 Kabinetga qaytish", callback_data="cabinet:back"))
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())
