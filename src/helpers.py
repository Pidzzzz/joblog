import os
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.helpers import escape_markdown
from telegram import Update

OWNER_ID = int(os.getenv("DEVELOPER_ID", "0"))

import json

HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "messages_history.json")

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                data = json.load(f)
                return (
                    {int(k): v for k, v in data.get("last_bot_messages", {}).items()},
                    {int(k): v for k, v in data.get("bot_message_history", {}).items()}
                )
        except Exception:
            pass
    return {}, {}

def save_history():
    try:
        serialized_last = {}
        for chat_id, val in last_bot_messages.items():
            if isinstance(val, int):
                serialized_last[chat_id] = val
            elif hasattr(val, "message_id"):
                serialized_last[chat_id] = val.message_id
            else:
                serialized_last[chat_id] = val

        data = {
            "last_bot_messages": serialized_last,
            "bot_message_history": bot_message_history
        }
        with open(HISTORY_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving history: {e}")

class PersistentDict(dict):
    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        save_history()
        
    def __delitem__(self, key):
        super().__delitem__(key)
        save_history()
        
    def pop(self, key, default=None):
        res = super().pop(key, default)
        save_history()
        return res
        
    def clear(self):
        super().clear()
        save_history()

def append_to_history(chat_id, message_id):
    if chat_id not in bot_message_history:
        bot_message_history[chat_id] = []
    if message_id not in bot_message_history[chat_id]:
        bot_message_history[chat_id].append(message_id)
    save_history()

def remove_from_history(chat_id, message_id):
    if chat_id in bot_message_history and message_id in bot_message_history[chat_id]:
        bot_message_history[chat_id].remove(message_id)
        save_history()

last_bot_messages = PersistentDict()
bot_message_history = PersistentDict()

_last, _hist = load_history()
for k, v in _last.items():
    dict.__setitem__(last_bot_messages, k, v)
for k, v in _hist.items():
    dict.__setitem__(bot_message_history, k, v)

delete_selections = {}
user_reminder_state = {}

bot_stats = {
    "messages_received": 0,
    "messages_sent": 0,
    "commands_used": 0,
    "callbacks_handled": 0,
    "tokens_used": 0,
    "start_time": None,
}


def estimate_tokens(text: str) -> int:
    return len(text) // 3


def _is_owner(update: Update) -> bool:
    return update.effective_user.id == OWNER_ID


def safe_delete_message(message):
    if not message:
        return
    async def _delete():
        try:
            await message.delete()
        except Exception:
            pass
    asyncio.create_task(_delete())


def _fmt_entry(e: dict) -> str:
    return f"  \\#{e['id']}  \\[{escape_markdown(e['time'], version=2)}\\]  {escape_markdown(e['text'], version=2)}"


def _fmt_entries(entries: list, title: str = None) -> str:
    if not entries:
        base = f"{escape_markdown(title, version=2)}\n\nTidak ada catatan\\." if title else "Tidak ada catatan\\."
        return base + "\n\n_Ketik atau kirim pesan langsung untuk mencatat_"
    lines = [f"*{escape_markdown(title, version=2)}*\n"] if title else []
    for e in entries:
        lines.append(_fmt_entry(e))
    return "\n".join(lines)


def _menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📝 Log Aktivitas", callback_data="menu_log"),
            InlineKeyboardButton("📅 Agenda Hari Ini", callback_data="menu_agenda"),
        ],
        [
            InlineKeyboardButton("⚔️ Rank Hunter", callback_data="menu_rank"),
            InlineKeyboardButton("📈 Statistik", callback_data="menu_stats"),
        ],
        [
            InlineKeyboardButton("🔍 Cari Log", callback_data="menu_search"),
            InlineKeyboardButton("🗂️ Arsip Harian", callback_data="menu_all"),
        ],
        [
            InlineKeyboardButton("⏰ Pengingat", callback_data="menu_reminder"),
            InlineKeyboardButton("🗑️ Hapus Log", callback_data="menu_clear"),
        ],
        [
            InlineKeyboardButton("🤖 AI Info", callback_data="menu_ai"),
            InlineKeyboardButton("📂 Projects", callback_data="menu_projects"),
        ],
        [
            InlineKeyboardButton("🍳 Pindai Makanan (AI)", callback_data="menu_scan_food"),
        ],
        [
            InlineKeyboardButton("❓ Panduan", callback_data="menu_help"),
            InlineKeyboardButton("🔄 Restart Bot", callback_data="menu_restart"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def _section_keyboard(section):
    if section == "log":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Log Baru", callback_data="menu_log"),
             InlineKeyboardButton("📅 Agenda", callback_data="menu_agenda")],
            [InlineKeyboardButton("🔍 Cari Log", callback_data="menu_search")],
            [InlineKeyboardButton("❌ Kembali", callback_data="menu_start")],
        ])
    elif section == "rank":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("⚔️ Rank Saya", callback_data="menu_rank"),
             InlineKeyboardButton("📈 Statistik", callback_data="menu_stats")],
            [InlineKeyboardButton("❌ Kembali", callback_data="menu_start")],
        ])
    elif section == "search":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Cari Log", callback_data="menu_search"),
             InlineKeyboardButton("🗂️ Arsip", callback_data="menu_all")],
            [InlineKeyboardButton("❌ Kembali", callback_data="menu_start")],
        ])
    elif section == "reminder":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Reminder Harian", callback_data="add_remind_daily")],
            [InlineKeyboardButton("➕ Reminder Sekali", callback_data="add_remind_once")],
            [InlineKeyboardButton("❌ Kembali", callback_data="menu_start")],
        ])
    elif section == "danger":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ Hapus Log", callback_data="menu_clear")],
            [InlineKeyboardButton("🔄 Restart Bot", callback_data="menu_restart")],
            [InlineKeyboardButton("❌ Kembali", callback_data="menu_start")],
        ])
    elif section == "scan_food":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Kembali", callback_data="menu_start")],
        ])
    return _menu_keyboard()


async def _send_and_auto_delete(message, text, delay=3):
    msg = await message.reply_text(text)
    chat_id = message.chat_id
    append_to_history(chat_id, msg.message_id)
    asyncio.create_task(_auto_delete_message(message.bot, chat_id, msg.message_id, delay))


async def _auto_delete_message(bot, chat_id, message_id, delay):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        remove_from_history(chat_id, message_id)
    except Exception:
        pass


async def _delete_all_bot_messages(chat_id, ctx=None, bot=None):
    deleted = 0
    bot_obj = bot if bot else (ctx.bot if ctx else None)
    
    old_msg = last_bot_messages.get(chat_id)
    if old_msg:
        try:
            if hasattr(old_msg, "delete"):
                await old_msg.delete()
                deleted += 1
            elif isinstance(old_msg, int) and bot_obj:
                await bot_obj.delete_message(chat_id=chat_id, message_id=old_msg)
                deleted += 1
        except Exception:
            pass
        last_bot_messages.pop(chat_id, None)
    
    if bot_obj:
        if chat_id in bot_message_history:
            for msg_id in list(bot_message_history[chat_id]):
                try:
                    await bot_obj.delete_message(chat_id=chat_id, message_id=msg_id)
                    deleted += 1
                except Exception:
                    pass
            bot_message_history[chat_id] = []
    
    print(f"[CLEANUP] Deleted {deleted} messages for chat {chat_id}")


async def _show_delete_list(query, entries, selected, user_id):
    lines = [f"🗑️ *Hapus Log* \\({len(entries)} catatan hari ini\\)\n"]
    lines.append("_Pilih log yang ingin dihapus, lalu tekan *Hapus Terpilih*_\n")
    for e in entries:
        check = "✅" if e["id"] in selected else "⬜"
        t = escape_markdown(e["time"][:5], version=2)
        txt = escape_markdown(e["text"], version=2)
        lines.append(f"{check} `#{e['id']}` `[{t}]` {txt}")
    msg = "\n".join(lines)

    keyboard = []
    for e in entries:
        label = f"{'✅' if e['id'] in selected else '⬜'} #{e['id']} {e['time'][:5]}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"toggle_del_{e['id']}")])

    btn_row = []
    if selected:
        btn_row.append(InlineKeyboardButton(f"🗑️ Hapus ({len(selected)})", callback_data="delete_selected"))
    btn_row.append(InlineKeyboardButton("🗑️ Hapus Semua", callback_data="delete_all_today"))
    btn_row.append(InlineKeyboardButton("❌ Batal", callback_data="menu_start"))
    keyboard.append(btn_row)

    await query.edit_message_text(msg, parse_mode="MarkdownV2", reply_markup=InlineKeyboardMarkup(keyboard))
