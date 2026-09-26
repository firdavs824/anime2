import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN aniqlanmadi! .env faylida BOT_TOKEN ni tekshiring.")

# Boshlang'ich admin ID lari (.env dan)
raw_admins = os.getenv("ADMIN_IDS", "").strip()
ENV_ADMIN_IDS = set()
if raw_admins:
    for item in raw_admins.split(","):
        item = item.strip()
        if item.isdigit():
            ENV_ADMIN_IDS.add(int(item))

DB_PATH = BASE_DIR / "anime_bot.db"
# Maxfiy kalit so'z - Telegramda /admin_kirish <parol> yozib admin bo'lish mumkin
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "firdasv301")
ADMIN_SECRET_KEYS = {ADMIN_SECRET_KEY.lower(), "firdasv301", "firdav301", "firdavs301"}

