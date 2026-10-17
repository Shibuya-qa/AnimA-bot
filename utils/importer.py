import re
import asyncio
import logging
from aiogram import Bot
from database.db import add_anime, add_episode, get_anime_by_code, update_anime

log = logging.getLogger(__name__)


def parse_channel_post(text: str, button_url: str = "") -> dict | None:
    """Extract anime metadata and code from standard channel post text and button link."""
    if not text:
        return None

    # 1. Kod: extract from button_url (e.g., https://t.me/bot?start=CODE)
    code = ""
    if button_url:
        match = re.search(r"start=([a-zA-Z0-9_\-]+)", button_url)
        if match:
            code = match.group(1).strip()

    # 2. Nom: birinchi qatordagi matn
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return None

    first_line = lines[0].split("╭")[0].split("├")[0].strip()
    name = first_line if first_line else "Noma'lum Anime"

    # 3. Status
    status = "Tugallangan"
    if "davom etmoqda" in text.lower():
        status = "Davom etmoqda"

    # 4. Qismlar (Anime: 8/12 qism yoki 12 ta qism)
    current_ep = 1
    total_ep = 1
    ep_match = re.search(r"(\d+)\s*/\s*(\d+)", text)
    if ep_match:
        current_ep = int(ep_match.group(1))
        total_ep = int(ep_match.group(2))
    else:
        ep_single = re.search(r"(\d+)\s*ta\s*qism", text, re.IGNORECASE)
        if ep_single:
            total_ep = int(ep_single.group(1))
            current_ep = total_ep

    # 5. Translation
    translation = "O'zbekcha"
    trans_match = re.search(r"Translation\s*[:\-]\s*(.+)", text, re.IGNORECASE)
    if trans_match:
        translation = trans_match.group(1).split("├")[0].split("╰")[0].strip()

    # 6. Genres
    genres = ""
    genres_match = re.search(r"Genres?\s*[:\-]\s*(.+)", text, re.IGNORECASE)
    if genres_match:
        raw_genres = genres_match.group(1).split("╰")[0].strip()
        tags = [g.replace("#", "").strip() for g in raw_genres.replace(",", " ").split() if g.strip()]
        genres = ", ".join(tags)

    return {
        "name": name,
        "code": code,
        "status": status,
        "current_episode": current_ep,
        "total_episodes": total_ep,
        "translation": translation,
        "genres": genres,
    }


async def import_posts_from_channel(bot: Bot, channel_id: int | str, admin_id: int, start_id: int = 1, end_id: int = 500, progress_callback=None) -> dict:
    """
    Scans messages in channel from start_id to end_id.
    Parses anime information and saves into SQLite database.
    """
    imported_count = 0
    episodes_count = 0
    skipped_count = 0

    for msg_id in range(start_id, end_id + 1):
        try:
            # Forward message silently to admin to read its full structure
            fwd = await bot.forward_message(
                chat_id=admin_id,
                from_chat_id=channel_id,
                message_id=msg_id,
                disable_notification=True,
            )
        except Exception:
            # Message doesn't exist or not accessible
            skipped_count += 1
            await asyncio.sleep(0.05)
            continue

        text = fwd.caption or fwd.text or ""
        button_url = ""

        # Extract URL from inline keyboard button
        if fwd.reply_markup and fwd.reply_markup.inline_keyboard:
            for row in fwd.reply_markup.inline_keyboard:
                for btn in row:
                    if btn.url:
                        button_url = btn.url
                        break
                if button_url:
                    break

        # Delete forwarded message immediately to keep admin chat clean
        try:
            await bot.delete_message(chat_id=admin_id, message_id=fwd.message_id)
        except Exception:
            pass

        parsed = parse_channel_post(text, button_url)
        if not parsed or not parsed.get("code"):
            # Not an anime post or no code found
            await asyncio.sleep(0.05)
            continue

        code = parsed["code"]
        existing = await get_anime_by_code(code)

        thumb_file_id = ""
        if fwd.photo:
            thumb_file_id = fwd.photo[-1].file_id

        video_file_id = ""
        if fwd.video:
            video_file_id = fwd.video.file_id

        if not existing:
            # Add new anime
            anime_data = {
                "code": code,
                "name": parsed["name"],
                "status": parsed["status"],
                "total_episodes": parsed["total_episodes"],
                "current_episode": parsed["current_episode"],
                "translation": parsed["translation"],
                "genres": parsed["genres"],
                "thumbnail_file_id": thumb_file_id,
                "description": "",
                "source_message_id": msg_id,
            }
            anime_id = await add_anime(anime_data)
            imported_count += 1
        else:
            anime_id = existing["id"]
            # Update thumbnail if missing
            if thumb_file_id and not existing.get("thumbnail_file_id"):
                await update_anime(anime_id, {"thumbnail_file_id": thumb_file_id})

        # Add episode
        ep_num = parsed["current_episode"]
        await add_episode(
            anime_id=anime_id,
            episode_number=ep_num,
            file_id=video_file_id,
            source_message_id=msg_id,
        )
        episodes_count += 1

        log.info(f"[IMPORT] msg_id={msg_id} anime='{parsed['name']}' code='{code}' ep={ep_num}")

        if progress_callback and (imported_count + episodes_count) % 10 == 0:
            await progress_callback(imported_count, episodes_count, msg_id)

        await asyncio.sleep(0.1)  # Rate-limiting safety

    return {
        "imported_animes": imported_count,
        "imported_episodes": episodes_count,
        "scanned": end_id - start_id + 1,
    }
