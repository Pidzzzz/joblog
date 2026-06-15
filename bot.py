# Load env before ANY other imports
from dotenv import load_dotenv
import os
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

import logging
from telegram.ext import ApplicationBuilder

from src.handlers import get_handlers
from src.scheduler import scheduler, restore_reminders

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("DEVELOPER_ID", "0"))

if not TOKEN:
    raise ValueError("BOT_TOKEN not found in .env")
if not OWNER_ID:
    raise ValueError("DEVELOPER_ID not found in .env")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

async def post_init(app):
    scheduler.start()
    restore_reminders(app.bot)
    print(f"SoloLeveling Journal Bot started. Owner: {OWNER_ID}")
    print(f"Reminders loaded and scheduler running.")

    restart_file = os.path.join(os.path.dirname(__file__), ".restart_chat")
    if os.path.exists(restart_file):
        try:
            with open(restart_file, "r") as f:
                chat_id = int(f.read().strip())
            await app.bot.send_message(
                chat_id=chat_id,
                text="✅ *Bot berhasil restart\\! Arise\\!*",
                parse_mode="MarkdownV2",
            )
        except Exception:
            pass
        finally:
            try:
                os.remove(restart_file)
            except Exception:
                pass

def main():
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()

    for h in get_handlers():
        app.add_handler(h)

    app.run_polling()

if __name__ == "__main__":
    main()
