import os
import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from aiogram.filters import Command, CommandObject
import logging

from database.db import (
    get_anime_by_code, get_anime_by_id, get_animes_by_name,
    add_history, add_favorite, remove_favorite, is_favorite,
    list_animes, count_animes,
    get_episodes, get_episode,
    increment_anime_views, increment_anime_downloads,
    search_animes, get_top_animes, get_random_anime,
    rate_anime, get_user_rating,
    get_all_genres, get_animes_by_genre, count_animes_by_genre,
)
from keyboards.main import (
    anime_actions, search_menu, catalog_keyboard,
    genres_keyboard, search_results_keyboard, top_animes_keyboard,
    rating_keyboard,
)
from config import SOURCE_CHANNEL_ID

router = Router()
log = logging.getLogger(__name__)

IGNORED_TEXTS = {
    "🔍 Qidirish", "🔍 Anime Izlash", "🔥 Top Animelar", "🎲 Random Anime",
    "🗂 Kabinet", "👑 Admin Panel", "Admin Panel", "📖 Qo'llanma",
    "📢 Reklama", "📱 Shorts", "admin", "panel"
}


def format_anime_card(anime: dict, current_ep_num: int = 1) -> str:
    status = anime.get("status", "Nomalum")
    status_emoji = "🟢" if status == "Tugallangan" else "🔄"
    total_ep = anime.get("total_episodes", 0)
    curr_total = anime.get("current_episode", 0)
    views = anime.get("views", 0) or 0
    downloads = anime.get("downloads", 0) or 0
    rating = anime.get("rating", 5.0) or 5.0
    rating_count = anime.get("rating_count", 0) or 0

    if status == "Tugallangan":
        ep_line = f"├‣ 📺 Qismlar: <b>{total_ep} ta</b>"
    else:
        ep_line = f"├‣ 📺 Qismlar: <b>{curr_total}/{total_ep}</b>"

    lines = [
        f"🎬 <b>{anime['name']}</b>",
        "╭────────────────────────────",
        f"├‣ 🔑 Kod: <code>{anime['code']}</code>",
        f"├‣ {status_emoji} Holati: <b>{status}</b>",
        ep_line,
        f"├‣ 📀 Tanlangan: <b>{current_ep_num}-qism</b>",
    ]
    if anime.get("translation"):
        lines.append(f"├‣ 🌐 Tarjima: <b>{anime['translation']}</b>")
    if anime.get("genres"):
        lines.append(f"├‣ 🎭 Janrlar: <i>{anime['genres']}</i>")

    lines.append("├────────────────────────────")
    stars = "⭐" * int(min(5, max(1, round(rating))))
    lines.append(f"├‣ 👁 Ko'rishlar: <b>{views:,}</b> | 📥 Yuklangan: <b>{downloads:,}</b>")
    lines.append(f"├‣ {stars} Reyting: <b>{rating:.1f}/5.0</b> ({rating_count} ovoz)")
    lines.append("╰────────────────────────────")

    if anime.get("description"):
        lines.append(f"\n📖 <b>Tavsif:</b>\n<i>{anime['description']}</i>")
    return "\n".join(lines)


async def send_episode_video(bot, chat_id: int, anime: dict, ep_num: int):
    """Deliver video for a specific episode and increment download count."""
    ep_data = await get_episode(anime["id"], ep_num)

    # If not found in primary anime, search sibling animes with same name
    if not ep_data or (not ep_data.get("file_id") and not ep_data.get("source_message_id")):
        siblings = await get_animes_by_name(anime["name"])
        for sib in siblings:
            if sib["id"] == anime["id"]:
                continue
            sib_ep = await get_episode(sib["id"], ep_num)
            if sib_ep and (sib_ep.get("file_id") or sib_ep.get("source_message_id")):
                ep_data = sib_ep
                break

    file_id = ep_data.get("file_id") if ep_data else ""
    msg_id = ep_data.get("source_message_id") if ep_data else 0

    # Fallback to single anime source_message_id if no specific ep found
    if not file_id and not msg_id:
        msg_id = anime.get("source_message_id", 0)

    caption_text = f"🎬 <b>{anime['name']}</b> — {ep_num}-qism\n🔑 Kod: <code>{anime['code']}</code>"

    if file_id:
        try:
            await bot.send_video(
                chat_id=chat_id,
                video=file_id,
                caption=caption_text,
                parse_mode="HTML",
                protect_content=True,
            )
            await increment_anime_downloads(anime["id"])
            return
        except Exception as e:
            log.error(f"[ANIME] send_video file_id failed: {e}")

    src_channel = os.getenv("SOURCE_CHANNEL_ID", SOURCE_CHANNEL_ID)
    if msg_id and src_channel:
        try:
            from_chat = int(src_channel) if str(src_channel).lstrip("-").isdigit() else src_channel
            await bot.copy_message(
                chat_id=chat_id,
                from_chat_id=from_chat,
                message_id=msg_id,
                caption=caption_text,
                parse_mode="HTML",
                protect_content=True,
            )
            await increment_anime_downloads(anime["id"])
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



async def deliver_anime(message: Message, anime: dict, ep_num: int = None, page: int = 0, user_id: int = None):
    """Send anime card then send video for selected episode."""
    if user_id is None:
        user_id = message.from_user.id if message.from_user else 0
    is_fav = await is_favorite(user_id, anime["id"]) if user_id else False

    await increment_anime_views(anime["id"])
    fresh_anime = await get_anime_by_id(anime["id"])
    if fresh_anime:
        anime = fresh_anime

    # Get episodes from this anime AND all sibling animes with same name
    episodes = await get_episodes(anime["id"])

    # Also pull episodes from same-name animes (e.g. mki1..mki12 all = "Mening kichik iblisim")
    siblings = await get_animes_by_name(anime["name"])
    sibling_ep_map = {}  # ep_number -> best (file_id, source_message_id)
    for sib in siblings:
        sib_eps = await get_episodes(sib["id"])
        for ep in sib_eps:
            en = ep["episode_number"]
            if en not in sibling_ep_map:
                sibling_ep_map[en] = ep
            else:
                # prefer entry with file_id
                if not sibling_ep_map[en].get("file_id") and ep.get("file_id"):
                    sibling_ep_map[en] = ep

    # Merge with primary episodes
    primary_map = {ep["episode_number"]: ep for ep in episodes}
    merged_map = {**sibling_ep_map, **primary_map}  # primary wins
    available_eps = sorted(merged_map.keys())

    if ep_num is None:
        curr = anime.get("current_episode", 1)
        if available_eps:
            if curr in available_eps:
                ep_num = curr
            else:
                ep_num = available_eps[0]
        else:
            ep_num = curr or 1


    caption = format_anime_card(anime, ep_num)
    kb = anime_actions(
        anime_id=anime["id"],
        is_fav=is_fav,
        active_ep=ep_num,
        available_episodes=available_eps,
        total_episodes=anime.get("total_episodes", 1),
        page=page,
        anime_code=anime.get("code", ""),
    )

    await add_history(user_id, anime["id"])

    # Send info card
    if anime.get("thumbnail_file_id"):
        await message.answer_photo(
            photo=anime["thumbnail_file_id"],
            caption=caption,
            parse_mode="HTML",
            reply_markup=kb
        )
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
        page=page,
        anime_code=anime.get("code", ""),
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
        page=page,
        anime_code=anime.get("code", ""),
    )

    try:
        if callback.message.caption:
            await callback.message.edit_reply_markup(reply_markup=kb)
        else:
            await callback.message.edit_reply_markup(reply_markup=kb)
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("download_ep:"))
async def download_ep_handler(callback: CallbackQuery):
    parts = callback.data.split(":")
    anime_id, ep_num = int(parts[1]), int(parts[2])
    anime = await get_anime_by_id(anime_id)
    if not anime:
        await callback.answer("Anime topilmadi", show_alert=True)
        return
    await callback.answer(f"📥 {ep_num}-qism yuborilmoqda...")
    await send_episode_video(callback.bot, callback.message.chat.id, anime, ep_num)


@router.callback_query(F.data.startswith("download_all:"))
async def download_all_handler(callback: CallbackQuery):
    """Send all available episodes one by one (including sibling animes)."""
    import asyncio
    anime_id = int(callback.data.split(":")[1])
    anime = await get_anime_by_id(anime_id)
    if not anime:
        await callback.answer("Anime topilmadi", show_alert=True)
        return

    # Collect episodes from all sibling animes (same name)
    sibling_ep_map = {}
    siblings = await get_animes_by_name(anime["name"])
    for sib in siblings:
        sib_eps = await get_episodes(sib["id"])
        for ep in sib_eps:
            en = ep["episode_number"]
            if en not in sibling_ep_map:
                sibling_ep_map[en] = ep
            elif not sibling_ep_map[en].get("file_id") and ep.get("file_id"):
                sibling_ep_map[en] = ep

    if not sibling_ep_map:
        await callback.answer("Qismlar topilmadi", show_alert=True)
        return

    all_ep_nums = sorted(sibling_ep_map.keys())
    await callback.answer(f"📦 Barcha {len(all_ep_nums)} ta qism yuborilmoqda...")

    notif = await callback.message.answer(
        f"⏳ <b>{anime['name']}</b> — barcha {len(all_ep_nums)} ta qism yuborilmoqda, kuting...",
        parse_mode="HTML"
    )

    for ep_num in all_ep_nums:
        await send_episode_video(callback.bot, callback.message.chat.id, anime, ep_num)
        await asyncio.sleep(0.5)  # flood avoid

    try:
        await notif.delete()
    except Exception:
        pass



# ─── RATINGS ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("rate_menu:"))
async def rate_menu_handler(callback: CallbackQuery):
    parts = callback.data.split(":")
    anime_id, active_ep, page = int(parts[1]), int(parts[2]), int(parts[3])
    await callback.message.edit_reply_markup(reply_markup=rating_keyboard(anime_id, active_ep, page))
    await callback.answer("⭐ Baho bering (1 dan 5 gacha)")


@router.callback_query(F.data.startswith("do_rate:"))
async def do_rate_handler(callback: CallbackQuery):
    parts = callback.data.split(":")
    anime_id, score, active_ep, page = int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4])
    result = await rate_anime(callback.from_user.id, anime_id, score)
    await callback.answer(f"✅ Rahmat! Siz {score} ⭐ baho berdingiz. Yangi reyting: {result['rating']:.1f}", show_alert=True)
    anime = await get_anime_by_id(anime_id)
    if anime:
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
            page=page,
            anime_code=anime.get("code", ""),
        )
        try:
            if callback.message.caption:
                await callback.message.edit_caption(caption=caption, parse_mode="HTML", reply_markup=kb)
            else:
                await callback.message.edit_text(text=caption, parse_mode="HTML", reply_markup=kb)
        except Exception:
            pass


# ─── SEARCH / EXPLORE ────────────────────────────────────────────────────────

@router.message(F.text.in_({"🔍 Qidirish", "🔍 Anime Izlash"}))
async def search_menu_handler(message: Message):
    total = await count_animes()
    text = (
        f"🔍 <b>Anime Qidiruv Markazi</b>\n\n"
        f"📚 Bazada jami <b>{total}</b> ta anime mavjud.\n\n"
        f"✨ Qidirmoqchi bo'lgan anime <b>nomini</b> yoki <b>kodini</b> yozib yuboring.\n"
        f"Misol: <code>81</code> yoki <code>Naruto</code>\n\n"
        f"Yoki pastdagi tugmalar orqali kashf eting:"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=search_menu())


@router.message(F.text == "🔥 Top Animelar")
@router.callback_query(F.data == "top_animes")
async def top_animes_handler(event: Message | CallbackQuery):
    top_list = await get_top_animes(limit=10)
    if not top_list:
        text = "📭 Hozircha animelar mavjud emas."
        if isinstance(event, CallbackQuery):
            await event.answer("Animelar yo'q", show_alert=True)
        else:
            await event.answer(text)
        return

    text = "🔥 <b>Eng mashhur TOP 10 Animelar:</b>\n\nTomosha qilish uchun birortasini tanlang:"
    kb = top_animes_keyboard(top_list)
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML", reply_markup=kb)


@router.message(F.text == "🎲 Random Anime")
@router.callback_query(F.data == "random_anime")
async def random_anime_handler(event: Message | CallbackQuery):
    anime = await get_random_anime()
    if not anime:
        msg = "📭 Hozircha bazada anime mavjud emas."
        if isinstance(event, CallbackQuery):
            await event.answer(msg, show_alert=True)
        else:
            await event.answer(msg)
        return

    target_msg = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await event.answer("🎲 Siz uchun tasodifiy anime tanlandi!")
    await deliver_anime(target_msg, anime)


@router.callback_query(F.data == "genres:list")
async def genres_list_handler(callback: CallbackQuery):
    genres = await get_all_genres()
    if not genres:
        await callback.answer("Hozircha janrlar qo'shilmagan", show_alert=True)
        return
    text = "🎭 <b>Janrlar bo'yicha saralash:</b>\n\nO'zingizga yoqqan janrni tanlang:"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=genres_keyboard(genres))
    await callback.answer()


@router.callback_query(F.data.startswith("genre:"))
async def genre_animes_handler(callback: CallbackQuery):
    parts = callback.data.split(":")
    genre, offset = parts[1], int(parts[2])
    animes = await get_animes_by_genre(genre, offset=offset, limit=8)
    total = await count_animes_by_genre(genre)
    if not animes:
        await callback.answer("Bu janrda anime yo'q", show_alert=True)
        return

    page = offset // 8 + 1
    total_pages = (total + 7) // 8
    text = f"🎭 <b>{genre}</b> janridagi animelar — {page}/{total_pages} sahifa (jami {total} ta):"
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=catalog_keyboard(animes, offset, total, genre=genre)
    )
    await callback.answer()


@router.callback_query(F.data == "search:menu")
async def search_menu_callback(callback: CallbackQuery):
    total = await count_animes()
    text = (
        f"🔍 <b>Anime Qidiruv Markazi</b>\n\n"
        f"📚 Bazada jami <b>{total}</b> ta anime mavjud.\n\n"
        f"✨ Anime <b>nomi</b> yoki <b>kodini</b> yuboring, yoki bo'lim tanlang:"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=search_menu())
    await callback.answer()


# ─── CATALOG ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("catalog:") & ~F.data.startswith("catalog:view:"))
async def catalog_handler(callback: CallbackQuery):
    offset = int(callback.data.split(":")[1])
    animes = await list_animes(offset=offset, limit=8)
    total = await count_animes()
    if not animes:
        await callback.answer("📭 Hali anime qo'shilmagan!", show_alert=True)
        return
    page = offset // 8 + 1
    total_pages = (total + 7) // 8
    text = (
        f"📋 <b>Animelar katalogi</b> — {page}/{total_pages} sahifa (jami {total} ta)\n\n"
        f"🟢 — tugallangan  |  🔄 — davom etmoqda"
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
        await callback.answer("Anime topilmadi", show_alert=True)
        return
    await callback.answer()
    await deliver_anime(callback.message, anime, user_id=callback.from_user.id)


@router.callback_query(F.data == "noop")
async def noop_handler(callback: CallbackQuery):
    await callback.answer()


# ─── TEXT SEARCH & CODE INPUT ────────────────────────────────────────────────

@router.message(Command("anime", "kod", "qidir", "search", ignore_mention=True))
@router.message(F.text & ~F.text.startswith("/") & ~F.text.in_(IGNORED_TEXTS))
async def search_or_code_handler(message: Message, command: CommandObject = None):
    bot_info = await message.bot.get_me()
    bot_username = (bot_info.username or "").lower() if bot_info else ""

    if command:
        if command.args:
            query = command.args.strip()
        else:
            if message.chat.type in ("group", "supergroup"):
                await message.answer(
                    "💡 <b>Guruhda anime qidirish:</b>\n\n"
                    "Anime nomi yoki kodini buyruqdan keyin yozing:\n"
                    "Misol: <code>/anime Naruto</code> yoki <code>/kod 15</code>",
                    parse_mode="HTML"
                )
            else:
                await message.answer(
                    "💡 Anime qidirish uchun nomini yoki kodini yozing.\n"
                    "Misol: <code>/anime Naruto</code> yoki <code>15</code>",
                    parse_mode="HTML"
                )
            return
    else:
        raw_text = (message.text or message.caption or "").strip()
        query = raw_text

        # Strip bot username mention if present:
        # e.g. "@animafundubbot Naruto" -> "Naruto"
        # e.g. "Naruto @animafundubbot" -> "Naruto"
        if bot_username:
            query = re.sub(rf"@{bot_username}\b", "", query, flags=re.IGNORECASE).strip()
            query = query.lstrip(":,; -").strip()

        # If user only tagged the bot without any query
        if not query:
            if message.chat.type in ("group", "supergroup"):
                await message.answer(
                    f"👋 <b>Guruhda anime qidirish:</b>\n\n"
                    f"Bot nomidan so'ng anime nomi yoki kodini yozing:\n"
                    f"• <code>@{bot_username} Naruto</code>\n"
                    f"• <code>@{bot_username} 15</code>\n\n"
                    f"Yoki <code>/anime Naruto</code> buyrug'idan foydalaning.",
                    parse_mode="HTML"
                )
            return

    # 1. Exact code match
    anime = await get_anime_by_code(query)
    if anime:
        await deliver_anime(message, anime)
        return

    # 2. Search by code prefix, name or genres
    results = await search_animes(query, limit=10)
    if len(results) == 1:
        await deliver_anime(message, results[0])
        return
    elif len(results) > 1:
        text = (
            f"🔍 <b>«{query}»</b> so'rovi bo'yicha {len(results)} ta natija topildi:\n\n"
            f"Ko'rmoqchi bo'lgan animengizni tanlang:"
        )
        await message.answer(text, parse_mode="HTML", reply_markup=search_results_keyboard(results))
        return

    # 3. No match found
    if message.chat.type in ("group", "supergroup"):
        await message.answer(
            f"❌ <b>«{query}»</b> bo'yicha hech qanday anime topilmadi.\n\n"
            f"💡 Anime nomi yoki kodini to'g'ri yozganingizni tekshiring.",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"❌ <b>«{query}»</b> bo'yicha hech qanday anime topilmadi.\n\n"
            f"💡 Qidiruvda xatolik bo'lmasligi uchun anime nomini yoki kodini tekshiring, yoki katalogdan qidiring.",
            parse_mode="HTML",
            reply_markup=search_menu()
        )


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
            page=page,
            anime_code=anime.get("code", ""),
        )
        await callback.message.edit_reply_markup(reply_markup=kb)


# ─── INLINE QUERY ────────────────────────────────────────────────────────────

@router.inline_query()
async def inline_search_handler(inline_query: InlineQuery):
    query = inline_query.query.strip()
    if query:
        results = await search_animes(query, limit=20)
    else:
        results = await get_top_animes(limit=15)

    bot_info = await inline_query.bot.get_me()
    items = []
    for anime in results:
        status_icon = "🟢" if anime.get("status") == "Tugallangan" else "🔄"
        rating = anime.get("rating", 5.0) or 5.0
        views = anime.get("views", 0) or 0
        desc = f"{status_icon} Kod: {anime['code']} | 👁 {views:,} | ⭐ {rating:.1f}"

        deep_link = f"https://t.me/{bot_info.username}?start={anime['code']}"
        text = (
            f"🎬 <b>{anime['name']}</b>\n"
            f"╭────────────────────────────\n"
            f"├‣ 🔑 Kod: <code>{anime['code']}</code>\n"
            f"├‣ {status_icon} Status: {anime['status']}\n"
            f"├‣ 👁 Ko'rishlar: {views:,} | ⭐ Reyting: {rating:.1f}\n"
            f"╰────────────────────────────\n\n"
            f"👉 <a href='{deep_link}'>Botda tomosha qilish va yuklab olish</a>"
        )
        thumb = anime.get("thumbnail_file_id") if anime.get("thumbnail_file_id", "").startswith("http") else None

        item = InlineQueryResultArticle(
            id=str(anime["id"]),
            title=f"{anime['name']} [{anime['code']}]",
            description=desc,
            input_message_content=InputTextMessageContent(
                message_text=text,
                parse_mode="HTML",
                disable_web_page_preview=False,
            ),
            thumbnail_url=thumb,
        )
        items.append(item)

    await inline_query.answer(items, cache_time=10, is_personal=True)
