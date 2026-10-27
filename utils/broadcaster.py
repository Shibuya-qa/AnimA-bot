import re
from aiogram import Bot
from config import SOURCE_CHANNEL_ID
from database.db import get_broadcast_channels


import os
import asyncio
import logging
from config import ADMIN_IDS
from database.db import add_episode, set_source_message_id

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

    admin_id = ADMIN_IDS[0]
    code = anime.get("code", "").strip().lower()
    if not code:
        return None

    import sqlite3
    from config import DB_PATH
    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        res = cur.execute("SELECT MAX(source_message_id) FROM anime_episodes").fetchone()
        max_id = (res[0] or 650) if res else 650
        con.close()
    except Exception:
        max_id = 650

    start_id = max_id + 30
    end_id = max(1, max_id - 70)

    code_regex = re.compile(rf"(?:anime\s*)?[ck]od(?:i)?\s*[:\-]?\s*{re.escape(code)}\b", re.IGNORECASE)

    for msg_id in range(start_id, end_id, -1):
        try:
            fwd = await bot.forward_message(
                chat_id=admin_id,
                from_chat_id=src_channel,
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

    lines = [
        f"<b>{anime['name']}</b>",
        "╭──────────────────────",
        f"├‣ Status: {status}",
        ep_line,
    ]
    if anime.get("translation"):
        lines.append(f"├‣ Translation: {anime['translation']}")
    if anime.get("genres"):
        lines.append(f"├‣ Genres: {anime['genres']}")
    lines.append("╰──────────────────────")
    if anime.get("description"):
        lines.append(f"\n📄 {anime['description']}")
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
