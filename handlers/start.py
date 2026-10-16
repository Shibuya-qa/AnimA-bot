from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, CommandObject

from database.db import register_user, get_anime_by_code
from keyboards.main import main_menu, cabinet_menu
from handlers.admin import check_admin

router = Router()

WELCOME_GIF = "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExcWd5ZzZ5ZzZ5ZzZ5ZzZ5ZzZ5ZzZ5ZzZ5ZzZ5ZzZ5ZzZ5ZzZ5Zz/giphy.gif"

WELCOME_TEXT = (
    "👋 <b>Assalomu alaykum, anime ixlosmandi!</b>\n\n"
    "🍿 <b>AnimAfundub</b> botiga xush kelibsiz!\n"
    "Bu yerda siz eng sara animelarni o'zbek tilida yuqori sifatda tomosha qilishingiz va yuklab olishingiz mumkin.\n\n"
    "✨ <b>Imkoniyatlar:</b>\n"
    "• 🔍 Kod yoki nom orqali tezkor qidiruv\n"
    "• 🔥 Eng mashhur TOP animelar reytingi\n"
    "• 🎲 Tasodifiy anime tanlash\n"
    "• 📜 Ko'rish tarixi va Sevimlilar ro'yxati\n\n"
    "👇 <i>Boshlash uchun menyudan kerakli bo'limni tanlang yoki anime kodini yuboring:</i>"
)


@router.message(CommandStart())
async def start_handler(message: Message, command: CommandObject = None):
    await register_user(
        user_id=message.from_user.id,
        username=message.from_user.username or "",
        full_name=message.from_user.full_name or "",
    )
    # Deep link: /start <anime_code>
    if command and command.args:
        code = command.args.strip()
        anime = await get_anime_by_code(code)
        if anime:
            from handlers.anime import deliver_anime
            await deliver_anime(message, anime)
            return

    is_adm = await check_admin(message.from_user.id)
    kb = main_menu(is_admin=is_adm)

    try:
        await message.answer_animation(
            animation=WELCOME_GIF,
            caption=WELCOME_TEXT,
            parse_mode="HTML",
            reply_markup=kb,
        )
    except Exception:
        await message.answer(
            text=WELCOME_TEXT,
            parse_mode="HTML",
            reply_markup=kb,
        )

