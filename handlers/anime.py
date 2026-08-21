from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
import logging

from database.db import (
    get_anime_by_code, get_anime_by_id,
    add_history, add_favorite, remove_favorite, is_favorite,
    list_animes, count_animes,
    get_episodes, get_episode,
)
from keyboards.main import anime_actions, search_menu, catalog_keyboard
from config import SOURCE_CHANNEL_ID

router = Router()
log = logging.getLogger(__name__)

IGNORED_TEXTS = {
    "🔍 Anime Izlash", "🗂 Kabinet", "📱 Shorts", "📖 Qo'llanma", "📢 Reklama"
}


def format_anime_card(anime: dict, current_ep_num: int = 1) -> str:
    status = anime.get("status", "Nomalum")
    total_ep = anime.get("total_episodes", 0)
    curr_total = anime.get("current_episode", 0)

    if status == "Tugallangan":
        ep_line = f"├‣ Anime: {total_ep} ta qism"
    else:
        ep_line = f"├‣ Anime: {curr_total}/{total_ep} qism"

    lines = [
        f"<b>{anime['name']}</b>",
        "╭──────────────────────",
        f"├‣ Status: {status}",
        ep_line,
        f"├‣ Tanlangan: <b>{current_ep_num}-qism</b>",
    ]
    if anime.get("translation"):
        lines.append(f"├‣ Translation: {anime['translation']}")
    if anime.get("genres"):
        lines.append(f"├‣ Genres: {anime['genres']}")
    lines.append("╰──────────────────────")
    if anime.get("description"):
        lines.append(f"\n📄 {anime['description']}")
    return "\n".join(lines)


async def send_episode_video(bot, chat_id: int, anime: dict, ep_num: int):
    """Deliver video for a specific episode."""
    ep_data = await get_episode(anime["id"], ep_num)
    file_id = ep_data.get("file_id") if ep_data else ""
    msg_id = ep_data.get("source_message_id") if ep_data else 0

    # Fallback to single anime source_message_id if ep_num == 1
    if not file_id and not msg_id and ep_num == 1:
        msg_id = anime.get("source_message_id", 0)

    if file_id:
        try:
            await bot.send_video(chat_id=chat_id, video=file_id, caption=f"🎬 <b>{anime['name']}</b> — {ep_num}-qism", parse_mode="HTML")
            return
        except Exception as e:
            log.error(f"[ANIME] send_video file_id failed: {e}")

    if msg_id and SOURCE_CHANNEL_ID:
        try:
            await bot.copy_message(
                chat_id=chat_id,
                from_chat_id=SOURCE_CHANNEL_ID,
                message_id=msg_id,
                caption=f"🎬 <b>{anime['name']}</b> — {ep_num}-qism",
                parse_mode="HTML",
            )
            log.info(f"[ANIME] copy_message OK: ep={ep_num} msg_id={msg_id}")
            return
        except Exception as e:
            log.error(f"[ANIME] copy_message failed: {e}")
            await bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ <b>Video yuborishda xato!</b>\n<code>{e}</code>",
                parse_mode="HTML"
            )
            return

    await bot.send_message(
        chat_id=chat_id,
        text=f"⏳ <b>{ep_num}-qism videosi hali yuklanmagan.</b>",
        parse_mode="HTML"
    )


async def deliver_anime(message: Message, anime: dict, ep_num: int = 1, page: int = 0):
    """Send anime card then send video for selected episode."""
    user_id = message.from_user.id
    is_fav = await is_favorite(user_id, anime["id"])

    episodes = await get_episodes(anime["id"])
    available_eps = [e["episode_number"] for e in episodes] if episodes else []

    caption = format_anime_card(anime, ep_num)
    kb = anime_actions(
        anime_id=anime["id"],
        is_fav=is_fav,
        active_ep=ep_num,
        available_episodes=available_eps,
        total_episodes=anime.get("total_episodes", 1),
        page=page
    )

    await add_history(user_id, anime["id"])

    # Send info card
    if anime.get("thumbnail_file_id"):
        await message.answer_photo(photo=anime["thumbnail_file_id"], caption=caption,
                                   parse_mode="HTML", reply_markup=kb)
    else:
        await message.answer(caption, parse_mode="HTML", reply_markup=kb)

    # Deliver video for selected episode
    await send_episode_video(message.bot, message.chat.id, anime, ep_num)


# ─── EPISODE CALLBACK ────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("ep:"))
async def episode_click_handler(callback: CallbackQuery):
    parts = callback.data.split(":")
    anime_id, ep_num, page = int(parts[1]), int(parts[2]), int(parts[3])
    anime = await get_anime_by_id(anime_id)
    if not anime:
        await callback.answer("Anime topilmadi", show_alert=True)
        return

    is_fav = await is_favorite(callback.from_user.id, anime_id)
    episodes = await get_episodes(anime_id)
    available_eps = [e["episode_number"] for e in episodes] if episodes else []

    caption = format_anime_card(anime, ep_num)
    kb = anime_actions(
        anime_id=anime_id,
        is_fav=is_fav,
        active_ep=ep_num,
        available_episodes=available_eps,
        total_episodes=anime.get("total_episodes", 1),
        page=page
    )

    try:
        if callback.message.caption:
            await callback.message.edit_caption(caption=caption, parse_mode="HTML", reply_markup=kb)
        else:
            await callback.message.edit_text(text=caption, parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass

    await callback.answer(f"▶️ {ep_num}-qism tanlandi")
    await send_episode_video(callback.bot, callback.message.chat.id, anime, ep_num)


@router.callback_query(F.data.startswith("ep_page:"))
async def episode_page_handler(callback: CallbackQuery):
    parts = callback.data.split(":")
    anime_id, active_ep, page = int(parts[1]), int(parts[2]), int(parts[3])
    anime = await get_anime_by_id(anime_id)
    if not anime:
        await callback.answer()
        return

    is_fav = await is_favorite(callback.from_user.id, anime_id)
    episodes = await get_episodes(anime_id)
    available_eps = [e["episode_number"] for e in episodes] if episodes else []

    caption = format_anime_card(anime, active_ep)
    kb = anime_actions(
        anime_id=anime_id,
        is_fav=is_fav,
        active_ep=active_ep,
        available_episodes=available_eps,
        total_episodes=anime.get("total_episodes", 1),
        page=page
    )

    try:
        if callback.message.caption:
            await callback.message.edit_reply_markup(reply_markup=kb)
        else:
            await callback.message.edit_reply_markup(reply_markup=kb)
    except Exception:
        pass
    await callback.answer()


# ─── SEARCH ──────────────────────────────────────────────────────────────────

@router.message(F.text == "🔍 Anime Izlash")
async def search_handler(message: Message):
    total = await count_animes()
    await message.answer(
        f"🔍 <b>Anime qidirish</b>\n\n"
        f"📚 Bazada jami <b>{total}</b> ta anime mavjud.\n\n"
        f"Kod bilsangiz — to'g'ridan-to'g'ri yuboring.\n"
        f"Bilmasangiz — katalogdan tanlang:",
        parse_mode="HTML",
        reply_markup=search_menu()
    )


@router.callback_query(F.data == "search:bycode")
async def search_by_code_hint(callback: CallbackQuery):
    await callback.message.edit_text(
        "✏️ Anime kodini yuboring (masalan: <code>81</code>):",
        parse_mode="HTML"
    )


# ─── CATALOG ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("catalog:") & ~F.data.startswith("catalog:view:"))
async def catalog_handler(callback: CallbackQuery):
    offset = int(callback.data.split(":")[1])
    animes = await list_animes(offset=offset)
    total = await count_animes()
    if not animes:
        await callback.answer("📭 Hali anime qo'shilmagan!", show_alert=True)
        return
    page = offset // 8 + 1
    total_pages = (total + 7) // 8
    text = (
        f"📋 <b>Animeler katalogi</b> — {page}/{total_pages} sahifa (jami {total} ta)\n\n"
        f"✅ — tugallangan  |  🔄 — davom etmoqda"
    )
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=catalog_keyboard(animes, offset, total))
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=catalog_keyboard(animes, offset, total))


@router.callback_query(F.data.startswith("catalog:view:"))
async def catalog_view_anime(callback: CallbackQuery):
    anime_id = int(callback.data.split(":")[2])
    anime = await get_anime_by_id(anime_id)
    if not anime:
        await callback.answer("Topilmadi", show_alert=True)
        return
    await callback.answer()
    await deliver_anime(callback.message, anime)


@router.callback_query(F.data == "noop")
async def noop_handler(callback: CallbackQuery):
    await callback.answer()


# ─── CODE INPUT ──────────────────────────────────────────────────────────────

@router.message(F.text & ~F.text.startswith("/") & ~F.text.in_(IGNORED_TEXTS))
async def code_handler(message: Message):
    code = message.text.strip()
    anime = await get_anime_by_code(code)
    if not anime:
        await message.answer(
            "❌ <b>Bunday kodli anime topilmadi!</b>\n\n"
            "📌 Kodni to'g'ri yozganingizni tekshiring yoki katalogdan qidiring.",
            parse_mode="HTML",
            reply_markup=search_menu()
        )
        return
    await deliver_anime(message, anime)


# ─── FAVORITES ───────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("fav:"))
async def favorite_handler(callback: CallbackQuery):
    parts = callback.data.split(":")
    anime_id = int(parts[1])
    active_ep = int(parts[2]) if len(parts) > 2 else 1
    page = int(parts[3]) if len(parts) > 3 else 0

    user_id = callback.from_user.id
    if await is_favorite(user_id, anime_id):
        await remove_favorite(user_id, anime_id)
        await callback.answer("💔 Sevimlilardan olib tashlandi")
        is_fav = False
    else:
        await add_favorite(user_id, anime_id)
        await callback.answer("❤️ Sevimlilarga qo'shildi!")
        is_fav = True

    anime = await get_anime_by_id(anime_id)
    if anime:
        episodes = await get_episodes(anime_id)
        available_eps = [e["episode_number"] for e in episodes] if episodes else []
        kb = anime_actions(
            anime_id=anime_id,
            is_fav=is_fav,
            active_ep=active_ep,
            available_episodes=available_eps,
            total_episodes=anime.get("total_episodes", 1),
            page=page
        )
        await callback.message.edit_reply_markup(reply_markup=kb)

