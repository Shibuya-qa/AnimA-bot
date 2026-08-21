import re
import logging
from aiogram import Router, F
from aiogram.types import Message
from database.db import set_source_message_id, get_anime_by_code, add_episode
from config import SOURCE_CHANNEL_ID

router = Router()
log = logging.getLogger(__name__)

CODE_PATTERN = re.compile(
    r"anime\s*[ck]odi\s*[:\-]?\s*([a-zA-Z0-9_\-]+)(?:[\s,]+(\d+)\s*[\-\s]*qism)?",
    re.IGNORECASE
)


@router.channel_post()
async def channel_post_indexer(message: Message):
    """Auto-index posts from source channel by anime code and episode number."""
    log.info(f"[CHANNEL] post received: chat_id={message.chat.id} msg_id={message.message_id}")

    if SOURCE_CHANNEL_ID and str(message.chat.id) != str(SOURCE_CHANNEL_ID):
        log.info(f"[CHANNEL] skip: not source channel ({message.chat.id} != {SOURCE_CHANNEL_ID})")
        return

    text = message.caption or message.text or ""
    match = CODE_PATTERN.search(text)
    if not match:
        log.info(f"[CHANNEL] no code found in: {text[:80]!r}")
        return

    raw_code = match.group(1).strip()
    ep_num = int(match.group(2)) if match.group(2) else 1

    anime = await get_anime_by_code(raw_code)
    code = raw_code

    # Handle dash episode syntax like 81-4 if 81 exists
    if not anime and "-" in raw_code:
        parts = raw_code.rsplit("-", 1)
        if parts[1].isdigit():
            possible_anime = await get_anime_by_code(parts[0])
            if possible_anime:
                anime = possible_anime
                code = parts[0]
                ep_num = int(parts[1])

    if anime:
        await add_episode(anime["id"], episode_number=ep_num, source_message_id=message.message_id)
        if ep_num == 1:
            await set_source_message_id(code, message.message_id)
        log.info(f"[CHANNEL] indexed: anime={anime['name']} code={code} ep={ep_num} message_id={message.message_id}")
    else:
        log.warning(f"[CHANNEL] code={raw_code!r} not found in DB")
