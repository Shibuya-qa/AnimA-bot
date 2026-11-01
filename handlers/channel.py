import os
import re
import logging
from aiogram import Router
from aiogram.types import Message
from database.db import set_source_message_id, get_anime_by_code, add_episode, find_anime_by_name_fuzzy
from config import SOURCE_CHANNEL_ID

router = Router()
log = logging.getLogger(__name__)

CODE_PATTERN = re.compile(
    r"(?:anime\s*)?[ck]od(?:i)?\s*[:\-]?\s*([a-zA-Z0-9_\-]+)(?:[\s,]+(\d+)(?:\s*[\-\s]*qism)?)?",
    re.IGNORECASE
)

EP_PATTERN = re.compile(
    r'\[\s*(\d+)\s*[-_]?\s*qism\s*\]|(\d+)\s*[-_]?\s*qism|qism\s*[:\-]?\s*(\d+)',
    re.IGNORECASE
)


@router.channel_post()
async def channel_post_indexer(message: Message):
    """Auto-index posts from source channel by anime code and episode number (both code and name formats)."""
    log.info(f"[CHANNEL] post received: chat_id={message.chat.id} msg_id={message.message_id}")

    current_source_id = os.getenv("SOURCE_CHANNEL_ID", SOURCE_CHANNEL_ID)
    if current_source_id and str(message.chat.id) != str(current_source_id):
        log.info(f"[CHANNEL] skip: not source channel ({message.chat.id} != {current_source_id})")
        return

    text = message.caption or message.text or ""
    if not text.strip():
        return

    match = CODE_PATTERN.search(text)
    
    anime = None
    code = ""
    raw_code = ""
    ep_num = None

    # 1. Extract episode number if mentioned anywhere in text
    ep_match = EP_PATTERN.search(text)
    if ep_match:
        ep_num = int(ep_match.group(1) or ep_match.group(2) or ep_match.group(3))

    # 2. Try matching by code
    if match:
        raw_code = match.group(1).strip()
        raw_ep = match.group(2)
        if raw_ep and ep_num is None:
            ep_num = int(raw_ep)
        anime = await get_anime_by_code(raw_code)
        code = raw_code

        # If code not found directly, try prefix/digits split (e.g. usq2 -> usq1, sjs9 -> sjs + ep 9)
        if not anime and raw_code:
            if "-" in raw_code:
                parts = raw_code.rsplit("-", 1)
                if parts[1].isdigit():
                    possible_anime = await get_anime_by_code(parts[0]) or await get_anime_by_code(f"{parts[0]}1")
                    if possible_anime:
                        anime = possible_anime
                        code = parts[0]
                        if ep_num is None:
                            ep_num = int(parts[1])
            if not anime:
                digit_match = re.search(r"^([a-zA-Z_\-]+)(\d+)$", raw_code)
                if digit_match:
                    prefix, digits = digit_match.group(1), digit_match.group(2)
                    possible_anime = await get_anime_by_code(prefix) or await get_anime_by_code(f"{prefix}1")
                    if possible_anime:
                        anime = possible_anime
                        code = prefix
                        if ep_num is None:
                            ep_num = int(digits)

    # 3. If code not found or not present, match by Anime Name (e.g. "Uni sevib qolosh uchun sabab [1-qism]")
    if not anime:
        anime = await find_anime_by_name_fuzzy(text)
        if anime:
            code = anime["code"]

    if anime:
        # Determine smart episode number if not explicitly specified
        if ep_num is None:
            if anime.get("current_episode") and anime["current_episode"] > 0:
                ep_num = anime["current_episode"]
            elif raw_code:
                digit_match = re.search(r"(\d+)$", raw_code)
                ep_num = int(digit_match.group(1)) if digit_match else 1
            else:
                ep_num = 1

        video_file_id = message.video.file_id if message.video else (message.document.file_id if message.document else "")
        await add_episode(
            anime["id"],
            episode_number=ep_num,
            file_id=video_file_id,
            source_message_id=message.message_id
        )
        await set_source_message_id(anime["code"], message.message_id)
        log.info(f"[CHANNEL] successfully indexed: anime='{anime['name']}' code='{code}' ep={ep_num} msg_id={message.message_id} video={'YES' if video_file_id else 'NO'}")
    else:
        log.warning(f"[CHANNEL] could not match anime from post: {text[:80]!r}")
