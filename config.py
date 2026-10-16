import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()] if os.getenv("ADMIN_IDS") else []
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
SOURCE_CHANNEL_ID = os.getenv("SOURCE_CHANNEL_ID", "")  # kanal where videos are stored
DB_PATH = "anime_bot.db"
