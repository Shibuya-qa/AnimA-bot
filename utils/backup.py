import asyncio
import os
import logging
from datetime import datetime
from aiogram.types import FSInputFile
from config import ADMIN_IDS, DB_PATH

log = logging.getLogger(__name__)


async def send_backup(bot, admin_id: int, note: str = ""):
    """Send anime_bot.db sqlite file directly to admin Telegram chat."""
    if not os.path.exists(DB_PATH):
        log.warning(f"[BACKUP] DB file {DB_PATH} not found.")
        return

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    caption = (
        f"🧠 <b>Bot xotirasi (Baza zaxirasi / Backup)</b>\n"
        f"📅 Sana: <code>{now_str}</code>\n"
        + (f"📌 Izoh: <b>{note}</b>\n" if note else "")
        + "\n<i>💡 Ushbu <code>anime_bot.db</code> faylini loyiha papkasiga joylashtirib botni ishga tushirsangiz, barcha animelar, qismlar va statistika 100% tiklanadi.</i>"
    )
    backup_filename = f"anime_bot_{datetime.now().strftime('%Y%m%d_%H%M')}.db"
    doc = FSInputFile(DB_PATH, filename=backup_filename)

    try:
        await bot.send_document(
            chat_id=admin_id,
            document=doc,
            caption=caption,
            parse_mode="HTML"
        )
        log.info(f"[BACKUP] Successfully sent backup to admin {admin_id}")
    except Exception as e:
        log.error(f"[BACKUP] Failed to send backup to {admin_id}: {e}")


async def daily_backup_scheduler(bot):
    """Runs continuously in background, fires daily at exactly 22:25 local time."""
    last_sent_date = None
    log.info("[BACKUP] Daily 22:25 backup scheduler started.")
    while True:
        try:
            now = datetime.now()
            # Har kechgi soat 22:25 da
            if now.hour == 22 and now.minute == 25:
                today_str = now.strftime("%Y-%m-%d")
                if last_sent_date != today_str:
                    log.info("[BACKUP] It is 22:25! Sending daily backups to admins...")
                    for admin_id in ADMIN_IDS:
                        await send_backup(bot, admin_id, note="Har kungi rejaviy zaxira (22:25)")
                    last_sent_date = today_str
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            log.info("[BACKUP] Scheduler stopped.")
            break
        except Exception as e:
            log.error(f"[BACKUP] Scheduler error: {e}")
            await asyncio.sleep(60)
