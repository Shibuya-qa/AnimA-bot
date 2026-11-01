import os
import re
import html
import asyncio
import logging
import sqlite3
from aiogram import Bot
from config import SOURCE_CHANNEL_ID, ADMIN_IDS, DB_PATH
from database.db import get_broadcast_channels, add_episode, set_source_message_id

log = logging.getLogger(__name__)

CODE_PATTERN = re.compile(r"anime\s*[ck]odi\s*[:\-]?\s*(\w+)", re.IGNORECASE)


async def search_and_link_channel_post(bot: Bot, anime: dict, ep_num: int = 1) -> dict | None:
    """
    Search SOURCE_CHANNEL_ID for recent posts matching the anime code.
    If found, saves episode and returns dict(file_id=..., source_message_id=...).
    """
    src_channel = os.getenv("SOURCE_CHANNEL_ID", SOURCE_CHANNEL_ID)
    if not src_channel or not ADMIN_IDS:
        return None

    from_chat = int(src_channel) if str(src_channel).lstrip("-").isdigit() else src_channel
    admin_id = ADMIN_IDS[0]
    code = anime.get("code", "").strip().lower()
    if not code:
        return None

    try:
        with sqlite3.connect(DB_PATH) as con:
            cur = con.cursor()
            res = cur.execute("SELECT MAX(source_message_id) FROM anime_episodes").fetchone()
            max_id = (res[0] or 650) if res else 650
    except Exception:
        max_id = 650

    start_id = max_id + 30
    end_id = max(1, max_id - 70)

    code_regex = re.compile(rf"(?:anime\s*)?[ck]od(?:i)?\s*[:\-]?\s*{re.escape(code)}\b", re.IGNORECASE)

    for msg_id in range(start_id, end_id, -1):
        try:
            fwd = await bot.forward_message(
                chat_id=admin_id,
                from_chat_id=from_chat,
                message_id=msg_id,
                disable_notification=True
            )
            text = fwd.caption or fwd.text or ""
            video_file_id = fwd.video.file_id if fwd.video else ""
            await bot.delete_message(chat_id=admin_id, message_id=fwd.message_id)

            if code_regex.search(text) or (code in text.lower() and anime.get("name", "").lower() in text.lower()):
                await add_episode(
                    anime_id=anime["id"],
                    episode_number=ep_num,
                    file_id=video_file_id,
                    source_message_id=msg_id
                )
                await set_source_message_id(anime["code"], msg_id)
                log.info(f"[AUTO-LINK] Found and linked {code} ep {ep_num} to msg_id {msg_id}")
                return {"file_id": video_file_id, "source_message_id": msg_id}
        except Exception:
            pass
        await asyncio.sleep(0.04)

    return None


def format_broadcast_caption(anime: dict) -> str:
    status = anime.get("status", "Nomalum")
    total_ep = anime.get("total_episodes", 0)
    current_ep = anime.get("current_episode", 0)

    if status == "Tugallangan":
        ep_line = f"├‣ Anime: {total_ep} ta qism"
    else:
        ep_line = f"├‣ Anime: {current_ep}/{total_ep} qism"

    name_esc = html.escape(str(anime.get("name", "")))
    status_esc = html.escape(str(status))

    lines = [
        f"<b>{name_esc}</b>",
        "╭──────────────────────",
        f"├‣ Status: {status_esc}",
        ep_line,
    ]
    if anime.get("translation"):
        trans_esc = html.escape(str(anime["translation"]))
        lines.append(f"├‣ Translation: {trans_esc}")
    if anime.get("genres"):
        genres_esc = html.escape(str(anime["genres"]))
        lines.append(f"├‣ Genres: {genres_esc}")
    lines.append("╰──────────────────────")
    if anime.get("description"):
        desc_esc = html.escape(str(anime["description"]))
        lines.append(f"\n📄 {desc_esc}")
    return "\n".join(lines)


async def broadcast_anime(bot: Bot, anime: dict, bot_username: str) -> dict:
    """
    Send anime announcement to all broadcast channels.
    Includes a 'Ko'rish' button that deep-links to the bot.
    Returns {success: int, failed: int}
    """
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    channels = await get_broadcast_channels()
    caption = format_broadcast_caption(anime)
    success, failed = 0, 0

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="▶️ Ko'rish",
        url=f"https://t.me/{bot_username}?start={anime['code']}"
    ))
    kb = builder.as_markup()

    for ch in channels:
        try:
            if anime.get("thumbnail_file_id"):
                await bot.send_photo(
                    chat_id=ch["channel_id"],
                    photo=anime["thumbnail_file_id"],
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=kb,
                )
            else:
                await bot.send_message(
                    chat_id=ch["channel_id"],
                    text=caption,
                    parse_mode="HTML",
                    reply_markup=kb,
                )
            success += 1
        except Exception as e:
            failed += 1

    return {"success": success, "failed": failed}
