# Load env before ANY other imports
from dotenv import load_dotenv
load_dotenv("D:/joblog/.env")

import os
from telegram.ext import ApplicationBuilder

from src.handlers import get_handlers

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("DEVELOPER_ID", "0"))

if not TOKEN:
    raise ValueError("BOT_TOKEN not found in .env")
if not OWNER_ID:
    raise ValueError("DEVELOPER_ID not found in .env")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    for h in get_handlers():
        app.add_handler(h)
    print(f"Bot started. Owner: {OWNER_ID}")
    app.run_polling()

if __name__ == "__main__":
    main()
