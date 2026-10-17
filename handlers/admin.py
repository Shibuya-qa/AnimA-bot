from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from config import ADMIN_IDS, ADMIN_PASSWORD, SOURCE_CHANNEL_ID
from database.db import (
    add_anime, delete_anime, update_anime, list_animes, count_animes,
    count_users, get_active_users_stats, get_anime_by_code, get_anime_by_id,
    is_admin_in_db, add_admin, list_admins,
    get_sub_channels, add_sub_channel, delete_sub_channel,
    get_broadcast_channels, add_broadcast_channel, delete_broadcast_channel,
    add_episode, get_episodes, get_episode, delete_episode,
)
from keyboards.main import (
    admin_menu, admin_anime_list, admin_anime_detail, admin_edit_fields,
    confirm_delete, sub_channels_menu, broadcast_channels_menu,
)
from utils.broadcaster import broadcast_anime, format_broadcast_caption

router = Router()


# ─── STATES ──────────────────────────────────────────────────────────────────

class PasswordState(StatesGroup):
    waiting = State()


class AddAnime(StatesGroup):
    code = State()
    name = State()
    status = State()
    total_episodes = State()
    current_episode = State()
    translation = State()
    genres = State()
    thumbnail = State()
    description = State()


class AddEpisode(StatesGroup):
    select_anime = State()
    episode_number = State()
    video_source = State()


class EditField(StatesGroup):
    waiting = State()


class AddSubChannel(StatesGroup):
    channel_id = State()
    channel_link = State()


class AddBroadcastChannel(StatesGroup):
    channel_id = State()


# ─── HELPERS ─────────────────────────────────────────────────────────────────

async def check_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS or await is_admin_in_db(user_id)


# ─── /panel & /admin ──────────────────────────────────────────────────────────

@router.message(Command("panel", "admin"))
@router.message(F.text.in_({"👑 Admin Panel", "Admin Panel", "admin", "panel"}))
async def panel_handler(message: Message, state: FSMContext):
    if await check_admin(message.from_user.id):
        await message.answer("👑 <b>Admin Panel</b>", parse_mode="HTML", reply_markup=admin_menu())
        return
    await state.set_state(PasswordState.waiting)
    await message.answer("🔐 <b>Parolni kiriting:</b>", parse_mode="HTML")


@router.message(PasswordState.waiting)
async def password_check(message: Message, state: FSMContext):
    try:
        await message.delete()
    except Exception:
        pass
    if message.text.strip() == ADMIN_PASSWORD:
        await add_admin(message.from_user.id, message.from_user.username or "", message.from_user.full_name or "")
        await state.clear()
        await message.answer("✅ <b>Siz admin bo'ldingiz!</b>", parse_mode="HTML", reply_markup=admin_menu())
    else:
        await state.clear()
        await message.answer("❌ <b>Parol noto'g'ri!</b>", parse_mode="HTML")


# ─── PANEL MAIN ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:back")
async def admin_back(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    await callback.message.edit_text("👑 <b>Admin Panel</b>", parse_mode="HTML", reply_markup=admin_menu())


@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    users = await count_users()
    active_stats = await get_active_users_stats()
    animes = await count_animes()
    admins = await list_admins()
    bch = await get_broadcast_channels()
    admin_list = "\n".join(f"  • {a['full_name']}" for a in admins) or "  —"
    text = (
        f"📊 <b>Statistika</b>\n\n"
        f"👤 Jami foydalanuvchilar: <b>{users}</b>\n"
        f"🔥 Aktiv (24 soat): <b>{active_stats['24h']}</b>\n"
        f"⚡ Aktiv (7 kun): <b>{active_stats['7d']}</b>\n"
        f"📅 Aktiv (30 kun): <b>{active_stats['30d']}</b>\n\n"
        f"🎬 Animeler: <b>{animes}</b>\n"
        f"📣 Broadcast kanallar: <b>{len(bch)}</b>\n\n"
        f"👑 Adminlar:\n{admin_list}"
    )
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🔙 Panel", callback_data="admin:back"))
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=b.as_markup())


@router.message(Command("backup"))
@router.callback_query(F.data == "admin:backup")
async def manual_backup_handler(event: Message | CallbackQuery):
    user_id = event.from_user.id
    if not await check_admin(user_id):
        return
    bot = event.bot
    if isinstance(event, CallbackQuery):
        await event.answer("📦 Zaxira fayli yuborilmoqda...")
    else:
        await event.answer("📦 Zaxira fayli tayyorlanmoqda...")
    from utils.backup import send_backup
    await send_backup(bot, user_id, note="Admin panelidan so'ralgan zaxira")


# ─── ANIME LIST ──────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin:list:"))
async def admin_list_handler(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    offset = int(callback.data.split(":")[2])
    animes = await list_animes(offset=offset)
    total = await count_animes()
    if not animes:
        await callback.answer("📋 Animeler yo'q", show_alert=True)
        return
    await callback.message.edit_text(
        f"📋 <b>Animeler ro'yxati</b> (jami: {total})",
        parse_mode="HTML",
        reply_markup=admin_anime_list(animes, offset, total)
    )


@router.callback_query(F.data.startswith("admin:anime:"))
async def admin_anime_detail_cb(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    anime_id = int(callback.data.split(":")[2])
    anime = await get_anime_by_id(anime_id)
    if not anime:
        await callback.answer("Topilmadi", show_alert=True)
        return
    has_video = "✅" if anime.get("source_message_id") else "❌"
    text = (
        f"🎬 <b>{anime['name']}</b>\n"
        f"🔑 Kod: <code>{anime['code']}</code>\n"
        f"📊 Status: {anime['status']}\n"
        f"📺 Qismlar: {anime['current_episode']}/{anime['total_episodes']}\n"
        f"🌐 Tarjima: {anime['translation']}\n"
        f"🎭 Janrlar: {anime['genres']}\n"
        f"🖼 Muqova: {'✅' if anime['thumbnail_file_id'] else '❌'}\n"
        f"📹 Video (kanal): {has_video}"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=admin_anime_detail(anime_id))


@router.callback_query(F.data.startswith("admin:rebroadcast:"))
async def admin_rebroadcast(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    anime_id = int(callback.data.split(":")[2])
    anime = await get_anime_by_id(anime_id)
    bot_info = await callback.bot.get_me()
    result = await broadcast_anime(callback.bot, anime, bot_info.username)
    await callback.answer(
        f"✅ Yuborildi: {result['success']} | ❌ Xato: {result['failed']}",
        show_alert=True
    )


@router.callback_query(F.data.startswith("admin:delete:"))
async def admin_delete_confirm(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    anime_id = int(callback.data.split(":")[2])
    await callback.message.edit_text(
        "🗑 <b>O'chirmoqchimisiz?</b>", parse_mode="HTML",
        reply_markup=confirm_delete(anime_id)
    )


@router.callback_query(F.data.startswith("admin:confirmdelete:"))
async def admin_do_delete(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    await delete_anime(int(callback.data.split(":")[2]))
    await callback.message.edit_text("✅ O'chirildi!", reply_markup=None)


# ─── ADD ANIME FSM ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:add")
async def admin_add_start(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback.from_user.id):
        return
    await state.set_state(AddAnime.code)
    await callback.message.answer(
        "🔑 <b>Anime kodini kiriting</b>\n"
        "Bu kod kanalda postni topish uchun ishlatiladi.\n"
        "Misol: <code>81</code>",
        parse_mode="HTML"
    )


@router.message(AddAnime.code)
async def add_code(message: Message, state: FSMContext):
    code = message.text.strip()
    if await get_anime_by_code(code):
        await message.answer("❌ Bu kod allaqachon mavjud! Boshqa kod kiriting:")
        return
    await state.update_data(code=code)
    await state.set_state(AddAnime.name)
    await message.answer("📝 Anime nomini kiriting:")


@router.message(AddAnime.name)
async def add_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AddAnime.status)
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ Tugallangan", callback_data="setstatus:Tugallangan"),
        InlineKeyboardButton(text="🔄 Davom etmoqda", callback_data="setstatus:Davom etmoqda"),
    )
    await message.answer("📊 Statusni tanlang:", reply_markup=b.as_markup())


@router.callback_query(F.data.startswith("setstatus:"), AddAnime.status)
async def add_status(callback: CallbackQuery, state: FSMContext):
    status = callback.data.split(":", 1)[1]
    await state.update_data(status=status)
    await state.set_state(AddAnime.total_episodes)
    await callback.message.edit_text(f"✅ Status: <b>{status}</b>", parse_mode="HTML")
    await callback.message.answer("🎬 Jami qismlar sonini kiriting:")


@router.message(AddAnime.total_episodes)
async def add_total_ep(message: Message, state: FSMContext):
    try:
        val = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Raqam kiriting!")
        return
    await state.update_data(total_episodes=val)
    await state.set_state(AddAnime.current_episode)
    await message.answer("📺 Joriy qism sonini kiriting:")


@router.message(AddAnime.current_episode)
async def add_current_ep(message: Message, state: FSMContext):
    try:
        val = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Raqam kiriting!")
        return
    await state.update_data(current_episode=val)
    await state.set_state(AddAnime.translation)
    await message.answer("🌐 Tarjima nomini kiriting:")


@router.message(AddAnime.translation)
async def add_translation(message: Message, state: FSMContext):
    await state.update_data(translation=message.text.strip())
    await state.set_state(AddAnime.genres)
    await message.answer("🎭 Janrlarni kiriting (masalan: Action, Drama):")


@router.message(AddAnime.genres)
async def add_genres(message: Message, state: FSMContext):
    await state.update_data(genres=message.text.strip())
    await state.set_state(AddAnime.thumbnail)
    await message.answer("🖼 Muqova rasmini yuboring (yoki /skip):")


@router.message(AddAnime.thumbnail, F.photo)
async def add_thumbnail(message: Message, state: FSMContext):
    await state.update_data(thumbnail_file_id=message.photo[-1].file_id)
    await state.set_state(AddAnime.description)
    await message.answer("📄 Qisqacha tavsif kiriting (yoki /skip):")


@router.message(AddAnime.thumbnail, F.text == "/skip")
async def add_thumbnail_skip(message: Message, state: FSMContext):
    await state.update_data(thumbnail_file_id="")
    await state.set_state(AddAnime.description)
    await message.answer("📄 Qisqacha tavsif kiriting (yoki /skip):")


@router.message(AddAnime.description)
async def add_description(message: Message, state: FSMContext):
    desc = "" if message.text.strip() == "/skip" else message.text.strip()
    await state.update_data(description=desc)
    data = await state.get_data()
    data.setdefault("thumbnail_file_id", "")
    data["source_message_id"] = 0
    await state.clear()

    anime_id = await add_anime(data)
    anime = await get_anime_by_id(anime_id)

    # Search source channel for the post
    status_text = ""
    if SOURCE_CHANNEL_ID:
        status_text = (
            f"\n\n⏳ Bot manba kanaldan <code>{data['code']}</code> kodli postni qidirmoqda...\n"
            f"Agar post allaqachon kanalda bo'lsa — avtomatik topiladi.\n"
            f"Aks holda kanalga post qo'shgach avtomatik indekslanadi."
        )
    else:
        status_text = "\n\n⚠️ SOURCE_CHANNEL_ID sozlanmagan! .env faylini tekshiring."

    await message.answer(
        f"✅ <b>Anime qo'shildi!</b>\n\n"
        f"📝 Nom: {data['name']}\n"
        f"🔑 Kod: <code>{data['code']}</code>"
        + status_text,
        parse_mode="HTML"
    )

    # Broadcast to all channels
    bch = await get_broadcast_channels()
    if bch:
        bot_info = await message.bot.get_me()
        result = await broadcast_anime(message.bot, anime, bot_info.username)
        await message.answer(
            f"📣 <b>Broadcast:</b> {result['success']} kanalga yuborildi"
            + (f", {result['failed']} ta xato" if result['failed'] else ""),
            parse_mode="HTML",
            reply_markup=admin_menu()
        )
    else:
        await message.answer(
            "ℹ️ Broadcast kanallari qo'shilmagan. Qo'shish uchun paneldan <b>Broadcast kanallar</b> bo'limiga kiring.",
            parse_mode="HTML",
            reply_markup=admin_menu()
        )


# ─── ADD EPISODE FSM ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:addep_select")
async def admin_addep_select_start(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback.from_user.id):
        return
    await state.set_state(AddEpisode.select_anime)
    await callback.message.answer(
        "🎬 <b>Qaysi animega qism qo'shmoqchisiz?</b>\n\n"
        "Anime kodini kiriting (masalan: <code>81</code>):",
        parse_mode="HTML"
    )


@router.message(AddEpisode.select_anime)
async def addep_select_code(message: Message, state: FSMContext):
    code = message.text.strip()
    anime = await get_anime_by_code(code)
    if not anime:
        await message.answer("❌ Bunday kodli anime topilmadi! Qayta kiriting:")
        return
    await start_add_episode_for_anime(message, state, anime)


@router.callback_query(F.data.startswith("admin:addep:"))
async def admin_addep_for_id(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback.from_user.id):
        return
    anime_id = int(callback.data.split(":")[2])
    anime = await get_anime_by_id(anime_id)
    if not anime:
        await callback.answer("Anime topilmadi", show_alert=True)
        return
    await start_add_episode_for_anime(callback.message, state, anime)


async def start_add_episode_for_anime(target_msg: Message, state: FSMContext, anime: dict):
    next_ep = anime.get("current_episode", 0) + 1
    await state.update_data(anime_id=anime["id"], anime_name=anime["name"], anime_code=anime["code"])
    await state.set_state(AddEpisode.episode_number)

    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text=f"➕ {next_ep}-qismni qo'shish", callback_data=f"set_ep_num:{next_ep}"))

    await target_msg.answer(
        f"🎬 <b>{anime['name']}</b> (Kod: <code>{anime['code']}</code>)\n"
        f"📺 Joriy qismlar: <b>{anime['current_episode']}/{anime['total_episodes']}</b>\n\n"
        f"Qism raqamini kiriting yoki pastdagi tugmani bosing:",
        parse_mode="HTML",
        reply_markup=b.as_markup()
    )


@router.callback_query(F.data.startswith("set_ep_num:"), AddEpisode.episode_number)
async def set_ep_num_cb(callback: CallbackQuery, state: FSMContext):
    ep_num = int(callback.data.split(":")[1])
    await state.update_data(episode_number=ep_num)
    await state.set_state(AddEpisode.video_source)
    await callback.message.edit_text(
        f"📹 <b>{ep_num}-qism uchun videoni yuboring</b>\n\n"
        f"• Videoni botga to'g'ridan-to'g'ri yuboring\n"
        f"• Yoki manba kanaldagi post ID sini kiriting (masalan: <code>1234</code>):",
        parse_mode="HTML"
    )


@router.message(AddEpisode.episode_number)
async def set_ep_num_msg(message: Message, state: FSMContext):
    try:
        ep_num = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Qism raqamini to'g'ri kiriting (masalan: 4):")
        return
    await state.update_data(episode_number=ep_num)
    await state.set_state(AddEpisode.video_source)
    await message.answer(
        f"📹 <b>{ep_num}-qism uchun videoni yuboring</b>\n\n"
        f"• Videoni botga to'g'ridan-to'g'ri yuboring\n"
        f"• Yoki manba kanaldagi post ID sini kiriting (masalan: <code>1234</code>):",
        parse_mode="HTML"
    )


@router.message(AddEpisode.video_source, F.video)
async def save_ep_video(message: Message, state: FSMContext):
    data = await state.get_data()
    file_id = message.video.file_id
    await add_episode(
        anime_id=data["anime_id"],
        episode_number=data["episode_number"],
        file_id=file_id,
        source_message_id=0
    )
    await state.clear()
    await message.answer(
        f"✅ <b>{data['anime_name']} — {data['episode_number']}-qism qo'shildi!</b>",
        parse_mode="HTML",
        reply_markup=admin_menu()
    )


@router.message(AddEpisode.video_source, F.document)
async def save_ep_document(message: Message, state: FSMContext):
    data = await state.get_data()
    file_id = message.document.file_id
    await add_episode(
        anime_id=data["anime_id"],
        episode_number=data["episode_number"],
        file_id=file_id,
        source_message_id=0
    )
    await state.clear()
    await message.answer(
        f"✅ <b>{data['anime_name']} — {data['episode_number']}-qism qo'shildi!</b>",
        parse_mode="HTML",
        reply_markup=admin_menu()
    )


@router.message(AddEpisode.video_source, F.text)
async def save_ep_msg_id(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        msg_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Kanal post ID sini raqam sifatida kiriting yoki video fayl yuboring!")
        return

    await add_episode(
        anime_id=data["anime_id"],
        episode_number=data["episode_number"],
        file_id="",
        source_message_id=msg_id
    )
    await state.clear()
    await message.answer(
        f"✅ <b>{data['anime_name']} — {data['episode_number']}-qism (Kanal post #{msg_id}) qo'shildi!</b>",
        parse_mode="HTML",
        reply_markup=admin_menu()
    )


# ─── EDIT FIELD ──────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin:edit:"))
async def admin_edit_menu(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    anime_id = int(callback.data.split(":")[2])
    await callback.message.edit_text(
        "✏️ <b>Qaysi maydonni tahrirlaysiz?</b>",
        parse_mode="HTML",
        reply_markup=admin_edit_fields(anime_id)
    )


@router.callback_query(F.data.startswith("admin:editfield:"))
async def admin_edit_field_start(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback.from_user.id):
        return
    parts = callback.data.split(":")
    anime_id, field = int(parts[2]), parts[3]
    await state.set_state(EditField.waiting)
    await state.update_data(anime_id=anime_id, field=field)
    if field == "thumbnail_file_id":
        await callback.message.answer("🖼 Yangi muqova rasmini yuboring:")
    else:
        await callback.message.answer(f"✏️ <code>{field}</code> uchun yangi qiymat:", parse_mode="HTML")


@router.message(EditField.waiting)
async def admin_edit_field_save(message: Message, state: FSMContext):
    data = await state.get_data()
    field, anime_id = data["field"], data["anime_id"]
    if field == "thumbnail_file_id" and message.photo:
        value = message.photo[-1].file_id
    elif field in {"total_episodes", "current_episode"}:
        try:
            value = int(message.text.strip())
        except ValueError:
            await message.answer("❌ Raqam kiriting!")
            return
    else:
        value = message.text.strip()
    await update_anime(anime_id, {field: value})
    await state.clear()
    await message.answer(f"✅ Yangilandi!", parse_mode="HTML", reply_markup=admin_menu())


# ─── SUBSCRIPTION CHANNELS ───────────────────────────────────────────────────

@router.callback_query(F.data == "admin:subchannels")
async def admin_sub_channels(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    channels = await get_sub_channels()
    text = (
        f"📢 <b>Majburiy obuna kanallari</b>\n"
        f"Foydalanuvchilar shu kanallarga obuna bo'lmasdan bot ishlatol olmaydi.\n\n"
        + ("\n".join(f"• {c['channel_name']}" for c in channels) if channels else "Hali yo'q.")
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=sub_channels_menu(channels))


@router.callback_query(F.data == "admin:addsubch")
async def admin_add_subch_start(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback.from_user.id):
        return
    await state.set_state(AddSubChannel.channel_id)
    await callback.message.answer(
        "📢 Kanal ID sini kiriting.\n"
        "Misol: <code>-1001234567890</code>\n\n"
        "⚠️ Bot kanalga admin sifatida qo'shilgan bo'lishi kerak!",
        parse_mode="HTML"
    )


@router.message(AddSubChannel.channel_id)
async def add_subch_id(message: Message, state: FSMContext):
    try:
        chat = await message.bot.get_chat(message.text.strip())
        await state.update_data(channel_id=message.text.strip(), channel_name=chat.title)
        await state.set_state(AddSubChannel.channel_link)
        await message.answer(f"✅ <b>{chat.title}</b> topildi!\n\nKanal linkini kiriting (https://t.me/...):", parse_mode="HTML")
    except Exception:
        await message.answer("❌ Topilmadi! Bot admin bo'lganini va ID to'g'riligini tekshiring:")


@router.message(AddSubChannel.channel_link)
async def add_subch_link(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    await add_sub_channel(data["channel_id"], data["channel_name"], message.text.strip())
    channels = await get_sub_channels()
    await message.answer(f"✅ <b>{data['channel_name']}</b> qo'shildi!", parse_mode="HTML",
                         reply_markup=sub_channels_menu(channels))


@router.callback_query(F.data.startswith("admin:delsubch:"))
async def admin_del_subch(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    await delete_sub_channel(int(callback.data.split(":")[2]))
    channels = await get_sub_channels()
    text = (
        f"📢 <b>Majburiy obuna kanallari</b>\n\n"
        + ("\n".join(f"• {c['channel_name']}" for c in channels) if channels else "Hali yo'q.")
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=sub_channels_menu(channels))
    await callback.answer("✅ O'chirildi")


# ─── BROADCAST CHANNELS ──────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:bchannels")
async def admin_bchannels(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    channels = await get_broadcast_channels()
    text = (
        f"📣 <b>Broadcast kanallar</b>\n"
        f"Yangi anime qo'shilganda shu kanallarga post yuboriladi.\n\n"
        + ("\n".join(f"• {c['channel_name']}" for c in channels) if channels else "Hali yo'q.")
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=broadcast_channels_menu(channels))


@router.callback_query(F.data == "admin:addbch")
async def admin_add_bch_start(callback: CallbackQuery, state: FSMContext):
    if not await check_admin(callback.from_user.id):
        return
    await state.set_state(AddBroadcastChannel.channel_id)
    await callback.message.answer(
        "📣 Broadcast kanal ID sini kiriting.\n"
        "Misol: <code>-1001234567890</code>\n\n"
        "⚠️ Bot kanalga admin (post yuborish huquqi bilan) qo'shilgan bo'lishi kerak!",
        parse_mode="HTML"
    )


@router.message(AddBroadcastChannel.channel_id)
async def add_bch_id(message: Message, state: FSMContext):
    try:
        chat = await message.bot.get_chat(message.text.strip())
        await state.clear()
        await add_broadcast_channel(message.text.strip(), chat.title)
        channels = await get_broadcast_channels()
        await message.answer(f"✅ <b>{chat.title}</b> qo'shildi!", parse_mode="HTML",
                             reply_markup=broadcast_channels_menu(channels))
    except Exception:
        await message.answer("❌ Topilmadi! Bot admin bo'lganini va ID to'g'riligini tekshiring:")


@router.callback_query(F.data.startswith("admin:delbch:"))
async def admin_del_bch(callback: CallbackQuery):
    if not await check_admin(callback.from_user.id):
        return
    await delete_broadcast_channel(int(callback.data.split(":")[2]))
    channels = await get_broadcast_channels()
    text = (
        f"📣 <b>Broadcast kanallar</b>\n\n"
        + ("\n".join(f"• {c['channel_name']}" for c in channels) if channels else "Hali yo'q.")
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=broadcast_channels_menu(channels))
    await callback.answer("✅ O'chirildi")
