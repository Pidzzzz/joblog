# Load env before ANY other imports
from dotenv import load_dotenv
import os
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

import logging
from telegram import BotCommand
from telegram.ext import ApplicationBuilder
from telegram.helpers import escape_markdown

from src.handlers import get_handlers
from src.helpers import _menu_keyboard
from src.scheduler import scheduler, restore_reminders
from src import storage
from src.ranks import get_xp_progress
from src.user_tracker import track_user, get_active_users

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


def get_start_text() -> str:
    s = storage.get_stats()
    xp = get_xp_progress(s["total"])
    rank = xp["rank"]
    return (
        "╔════════════════════════╗\n"
        "   ⚔️  *SOLO LEVELING JOURNAL*  ⚔️   \n"
        "╚════════════════════════╝\n\n"
        f"{rank['emoji']} *Rank:* `{escape_markdown(rank['rank'], version=2)}` \\— {escape_markdown(rank['title'], version=2)}\n\n"
        "Selamat datang, *Hunter*\\. Ini adalah log harian pribadi Anda\\.\n"
        "Setiap tugas, aktivitas, dan langkah perjalanan Anda akan direkam di sini\\.\n\n"
        "*Arise\\!* Mulai pencatatan Anda sekarang\\."
    )


async def post_init(app):
    scheduler.start()
    restore_reminders(app.bot)
    print(f"SoloLeveling Journal Bot started. Owner: {OWNER_ID}")
    print(f"Reminders loaded and scheduler running.")

    commands = [
        BotCommand("start", "Menu utama"),
        BotCommand("rank", "Cek Rank Hunter"),
        BotCommand("agenda", "Agenda hari ini"),
        BotCommand("log", "Catat kegiatan manual"),
        BotCommand("today", "Lihat catatan hari ini"),
        BotCommand("yesterday", "Lihat catatan kemarin"),
        BotCommand("date", "Catatan tanggal tertentu"),
        BotCommand("search", "Cari catatan lama"),
        BotCommand("all", "Arsip semua tanggal"),
        BotCommand("stats", "Statistik Hunter"),
        BotCommand("export", "Export jurnal ke PDF"),
        BotCommand("del", "Hapus catatan by ID"),
        BotCommand("clear", "Hapus log interaktif"),
        BotCommand("remind", "Reminder harian"),
        BotCommand("remindat", "Reminder sekali"),
        BotCommand("reminders", "Daftar reminder aktif"),
        BotCommand("unremind", "Hapus reminder"),
        BotCommand("projects", "Lihat proyek GitHub"),
        BotCommand("restart", "Restart bot"),
    ]
    await app.bot.set_my_commands(commands)
    print("Bot commands registered.")

    restart_chat_id = None
    restart_file = os.path.join(os.path.dirname(__file__), ".restart_chat")
    if os.path.exists(restart_file):
        try:
            with open(restart_file, "r") as f:
                restart_chat_id = int(f.read().strip())
            track_user(restart_chat_id)
        except Exception:
            pass
        finally:
            try:
                os.remove(restart_file)
            except Exception:
                pass

    active_users = get_active_users()
    if active_users:
        print(f"Sending update menu to {len(active_users)} active users...")
        sent = 0
        from src.helpers import _delete_all_bot_messages, last_bot_messages
        for uid in active_users:
            try:
                await _delete_all_bot_messages(uid, bot=app.bot)
                
                if uid == restart_chat_id:
                    menu_text = "✅ *Bot berhasil restart\\! Arise\\!*\n\n" + get_start_text()
                else:
                    menu_text = get_start_text()
                    
                msg = await app.bot.send_message(
                    chat_id=uid,
                    text=menu_text,
                    parse_mode="MarkdownV2",
                    reply_markup=_menu_keyboard(),
                )
                last_bot_messages[uid] = msg.message_id
                sent += 1
            except Exception as e:
                print(f"Error sending start menu to {uid}: {e}")
                pass
        print(f"Menu sent to {sent}/{len(active_users)} users.")

def main():
    import httpx
    from telegram.request import HTTPXRequest
    
    base_url = os.getenv("TELEGRAM_API_BASE_URL")
    
    transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0")
    request = HTTPXRequest(connect_timeout=20, read_timeout=20, httpx_kwargs={"transport": transport})
    
    builder = ApplicationBuilder().token(TOKEN).request(request).post_init(post_init)
    if base_url:
        builder = builder.base_url(base_url)
        if "/bot" in base_url:
            base_file_url = base_url.replace("/bot", "/file/bot")
            builder = builder.base_file_url(base_file_url)
            
    app = builder.build()

    # Wrap send_message and send_document to automatically track all sent messages
    from telegram.ext import ExtBot

    orig_send_message = ExtBot.send_message
    async def wrapped_send_message(self, *args, **kwargs):
        msg = await orig_send_message(self, *args, **kwargs)
        try:
            chat_id = kwargs.get("chat_id") or (args[0] if len(args) > 0 else None)
            if chat_id and msg and hasattr(msg, "message_id"):
                from src.helpers import append_to_history
                append_to_history(int(chat_id), msg.message_id)
        except Exception:
            pass
        return msg
    ExtBot.send_message = wrapped_send_message

    orig_send_document = ExtBot.send_document
    async def wrapped_send_document(self, *args, **kwargs):
        msg = await orig_send_document(self, *args, **kwargs)
        try:
            chat_id = kwargs.get("chat_id") or (args[0] if len(args) > 0 else None)
            if chat_id and msg and hasattr(msg, "message_id"):
                from src.helpers import append_to_history
                append_to_history(int(chat_id), msg.message_id)
        except Exception:
            pass
        return msg
    ExtBot.send_document = wrapped_send_document

    for h in get_handlers():
        app.add_handler(h)

    app.run_polling()

if __name__ == "__main__":
    main()
# Proxy base URL and Gemini key configured successfully
