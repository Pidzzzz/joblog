import os
import re
import asyncio
from datetime import date, datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.helpers import escape_markdown

from src import storage
from src import scheduler as sched
from src.ranks import get_rank, get_xp_progress, get_streak_info, format_progress_bar
from src.pdf_export import generate_pdf
from src.user_tracker import track_user

OWNER_ID = int(os.getenv("DEVELOPER_ID", "0"))

delete_selections = {}
last_bot_messages = {}
user_reminder_state = {}


async def _send_and_auto_delete(message, text, delay=3):
    msg = await message.reply_text(text)
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except Exception:
        pass


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
            InlineKeyboardButton("🔄 Restart Bot", callback_data="menu_restart"),
            InlineKeyboardButton("❓ Panduan", callback_data="menu_help"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


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


def get_agenda_text(chat_id: int) -> str:
    logs = storage.get_today()
    all_reminders = sched.get_reminders(chat_id)
    today_str = date.today().isoformat()
    
    # Filter reminders for today
    today_reminders = []
    for r in all_reminders:
        if r.get("repeat") == "daily":
            today_reminders.append(r)
        else:
            r_date = r.get("remind_at", "").split("T")[0]
            if r_date == today_str:
                today_reminders.append(r)
                
    # Sort logs by time (HH:MM:SS)
    logs_sorted = sorted(logs, key=lambda x: x.get("time", ""))
    
    # Sort reminders by time
    def get_reminder_time(r):
        time_part = r.get("remind_at", "").split("T")[1]
        return time_part[:5] # HH:MM
        
    reminders_sorted = sorted(today_reminders, key=get_reminder_time)
    
    # Format the message beautifully
    escaped_date = escape_markdown(today_str, version=2)
    lines = [
        "╔════════════════════════╗",
        "⚔️   *DAILY QUEST AGENDA*   ⚔️",
        "╚════════════════════════╝",
        f"📅 *Tanggal:* `{escaped_date}`\n",
        "🔴 *ACTIVE QUESTS \\(Reminders\\):*"
    ]
    
    if not reminders_sorted:
        lines.append("  _Tidak ada agenda/pengingat untuk hari ini\\._")
    else:
        for r in reminders_sorted:
            r_time = escape_markdown(get_reminder_time(r), version=2)
            r_text = escape_markdown(r["text"], version=2)
            lines.append(f"  ⏳ `[{r_time}]` {r_text}")
            
    lines.append("\n🟢 *CLEARED QUESTS \\(Aktivitas Tercatat\\):*")
    if not logs_sorted:
        lines.append("  _Belum ada aktivitas yang dicatat hari ini\\._")
    else:
        for l in logs_sorted:
            l_time = escape_markdown(l.get("time", "")[:5], version=2)
            l_text = escape_markdown(l.get("text", ""), version=2)
            lines.append(f"  ✅ `[{l_time}]` {l_text}")
            
    lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("_Ketik langsung pesan untuk mencatat log harian_")
    
    return "\n".join(lines)


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update):
        await update.message.reply_text("⛔ Bot ini pribadi.")
        return
    track_user(update.effective_chat.id)
    s = storage.get_stats()
    xp = get_xp_progress(s["total"])
    rank = xp["rank"]
    text = (
        "╔════════════════════════╗\n"
        "   ⚔️  *SOLO LEVELING JOURNAL*  ⚔️   \n"
        "╚════════════════════════╝\n\n"
        f"{rank['emoji']} *Rank:* `{escape_markdown(rank['rank'], version=2)}` \\— {escape_markdown(rank['title'], version=2)}\n\n"
        "Selamat datang, *Hunter*\\. Ini adalah log harian pribadi Anda\\.\n"
        "Setiap tugas, aktivitas, dan langkah perjalanan Anda akan direkam di sini\\.\n\n"
        "*Arise\\!* Mulai pencatatan Anda sekarang\\."
    )
    await update.message.reply_text(text, parse_mode="MarkdownV2", reply_markup=_menu_keyboard())


async def menu_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    print(f"[DEBUG] Callback received: {data}")

    if data == "menu_start":
        s = storage.get_stats()
        xp = get_xp_progress(s["total"])
        rank = xp["rank"]
        text = (
            "╔════════════════════════╗\n"
            "   ⚔️  *SOLO LEVELING JOURNAL*  ⚔️   \n"
            "╚════════════════════════╝\n\n"
            f"{rank['emoji']} *Rank:* `{escape_markdown(rank['rank'], version=2)}` \\— {escape_markdown(rank['title'], version=2)}\n\n"
            "Selamat datang, *Hunter*\\. Ini adalah log harian pribadi Anda\\.\n"
            "Setiap tugas, aktivitas, dan langkah perjalanan Anda akan direkam di sini\\.\n\n"
            "*Arise\\!* Mulai pencatatan Anda sekarang\\."
        )
        await query.edit_message_text(text, parse_mode="MarkdownV2", reply_markup=_menu_keyboard())
    elif data == "menu_log":
        await query.edit_message_text(
            "📝 *Log Aktivitas*\n\nKetik langsung pesan atau gunakan:\n`/log \\<aktivitas\\>` untuk mencatat kegiatan baru\\.",
            parse_mode="MarkdownV2",
            reply_markup=_menu_keyboard(),
        )
    elif data == "menu_agenda":
        msg = get_agenda_text(update.effective_user.id)
        await query.edit_message_text(msg, parse_mode="MarkdownV2", reply_markup=_menu_keyboard())
    elif data == "menu_today":
        entries = storage.get_today()
        today_str = date.today().isoformat()
        msg = _fmt_entries(entries, f"Hari Ini \\({today_str}\\)")
        if len(msg) > 4000:
            msg = msg[:4000] + "\n\n... \(terlalu panjang\)"
        await query.edit_message_text(msg, parse_mode="MarkdownV2", reply_markup=_menu_keyboard())
    elif data == "menu_date":
        await query.edit_message_text(
            "📅 *Cari Tanggal*\n\nGunakan:\n`/date YYYY\-MM\-DD`",
            parse_mode="MarkdownV2",
            reply_markup=_menu_keyboard(),
        )
    elif data == "menu_search":
        await query.edit_message_text(
            "🔍 *Cari Log*\n\nGunakan:\n`/search \\<kata kunci\\>` untuk mencari catatan lama\\.",
            parse_mode="MarkdownV2",
            reply_markup=_menu_keyboard(),
        )
    elif data == "menu_reminder":
        reminders = sched.get_reminders(update.effective_user.id)
        keyboard = [
            [InlineKeyboardButton("➕ Reminder Harian", callback_data="add_remind_daily")],
            [InlineKeyboardButton("➕ Reminder Sekali", callback_data="add_remind_once")],
        ]
        if reminders:
            keyboard.append([InlineKeyboardButton("📋 Lihat Semua Reminder", callback_data="list_reminders")])
            for r in reminders:
                rid = r['id']
                rtext = r['text'][:20]
                keyboard.append([InlineKeyboardButton(f"🗑️ #{rid} {rtext}", callback_data=f"del_remind_{rid}")])
        keyboard.append([InlineKeyboardButton("❌ Kembali", callback_data="menu_start")])
        
        if reminders:
            lines = ["⏰ *Reminder Aktif*\n"]
            for r in reminders:
                rid = r['id']
                rt = escape_markdown(r['remind_at'][:16], version=2)
                rtext = escape_markdown(r['text'], version=2)
                repeat = f" \\(_{escape_markdown(r['repeat'], version=2)}_\\)" if r['repeat'] else ""
                lines.append(f"  #{rid}  {rt}{repeat}  {rtext}")
            msg = "\n".join(lines)
        else:
            msg = "⏰ *Reminder*\n\nBelum ada reminder aktif\\.\nPilih opsi di bawah untuk menambahkan\\."
        await query.edit_message_text(msg, parse_mode="MarkdownV2", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "add_remind_daily":
        keyboard = [
            [InlineKeyboardButton("🌅 06:00", callback_data="set_daily_06:00"),
             InlineKeyboardButton("☀️ 07:00", callback_data="set_daily_07:00"),
             InlineKeyboardButton("🌤️ 08:00", callback_data="set_daily_08:00")],
            [InlineKeyboardButton("⏰ 09:00", callback_data="set_daily_09:00"),
             InlineKeyboardButton("🕙 10:00", callback_data="set_daily_10:00"),
             InlineKeyboardButton("🕚 11:00", callback_data="set_daily_11:00")],
            [InlineKeyboardButton("🕛 12:00", callback_data="set_daily_12:00"),
             InlineKeyboardButton("🕐 13:00", callback_data="set_daily_13:00"),
             InlineKeyboardButton("🕑 14:00", callback_data="set_daily_14:00")],
            [InlineKeyboardButton("🕒 15:00", callback_data="set_daily_15:00"),
             InlineKeyboardButton("🕓 16:00", callback_data="set_daily_16:00"),
             InlineKeyboardButton("🕔 17:00", callback_data="set_daily_17:00")],
            [InlineKeyboardButton("🕕 18:00", callback_data="set_daily_18:00"),
             InlineKeyboardButton("🕖 19:00", callback_data="set_daily_19:00"),
             InlineKeyboardButton("🕗 20:00", callback_data="set_daily_20:00")],
            [InlineKeyboardButton("✏️ Jam Lain", callback_data="set_daily_custom")],
            [InlineKeyboardButton("❌ Kembali", callback_data="menu_reminder")],
        ]
        await query.edit_message_text(
            "⏰ *Reminder Harian*\nPilih jam:",
            parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    elif data == "add_remind_once":
        today = date.today().isoformat()
        keyboard = [
            [InlineKeyboardButton("📅 Hari Ini", callback_data=f"set_once_{today}")],
            [InlineKeyboardButton("📅 Besok", callback_data=f"set_once_{(date.today() + timedelta(days=1)).isoformat()}")],
            [InlineKeyboardButton("📅 Lusa", callback_data=f"set_once_{(date.today() + timedelta(days=2)).isoformat()}")],
            [InlineKeyboardButton("✏️ Tanggal Lain", callback_data="set_once_custom")],
            [InlineKeyboardButton("❌ Kembali", callback_data="menu_reminder")],
        ]
        await query.edit_message_text(
            "⏰ *Reminder Sekali*\nPilih tanggal:",
            parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    elif data.startswith("set_daily_"):
        time_str = data.replace("set_daily_", "")
        if time_str == "custom":
            await query.edit_message_text(
                "✏️ *Ketik jam manual:*\nFormat: `HH:MM`\nContoh: `09:30`",
                parse_mode="MarkdownV2",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data="add_remind_daily")]]),
            )
            user_reminder_state[update.effective_user.id] = {"type": "daily", "step": "time"}
        else:
            user_reminder_state[update.effective_user.id] = {"type": "daily", "time": time_str, "step": "text"}
            await query.edit_message_text(
                f"⏰ Reminder harian jam *{time_str}*\n\nKetik pesan reminder:",
                parse_mode="MarkdownV2",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data="add_remind_daily")]]),
            )
    elif data.startswith("set_once_"):
        date_str = data.replace("set_once_", "")
        if date_str == "custom":
            await query.edit_message_text(
                "✏️ *Ketik tanggal manual:*\nFormat: `YYYY\-MM\-DD`\nContoh: `2026\-06\-20`",
                parse_mode="MarkdownV2",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data="add_remind_once")]]),
            )
            user_reminder_state[update.effective_user.id] = {"type": "once", "step": "date"}
        else:
            keyboard = [
                [InlineKeyboardButton("🌅 06:00", callback_data=f"set_once_time_{date_str}_06:00"),
                 InlineKeyboardButton("☀️ 07:00", callback_data=f"set_once_time_{date_str}_07:00"),
                 InlineKeyboardButton("🌤️ 08:00", callback_data=f"set_once_time_{date_str}_08:00")],
                [InlineKeyboardButton("⏰ 09:00", callback_data=f"set_once_time_{date_str}_09:00"),
                 InlineKeyboardButton("🕙 10:00", callback_data=f"set_once_time_{date_str}_10:00"),
                 InlineKeyboardButton("🕚 11:00", callback_data=f"set_once_time_{date_str}_11:00")],
                [InlineKeyboardButton("🕛 12:00", callback_data=f"set_once_time_{date_str}_12:00"),
                 InlineKeyboardButton("🕐 13:00", callback_data=f"set_once_time_{date_str}_13:00"),
                 InlineKeyboardButton("🕑 14:00", callback_data=f"set_once_time_{date_str}_14:00")],
                [InlineKeyboardButton("🕒 15:00", callback_data=f"set_once_time_{date_str}_15:00"),
                 InlineKeyboardButton("🕓 16:00", callback_data=f"set_once_time_{date_str}_16:00"),
                 InlineKeyboardButton("🕔 17:00", callback_data=f"set_once_time_{date_str}_17:00")],
                [InlineKeyboardButton("🕕 18:00", callback_data=f"set_once_time_{date_str}_18:00"),
                 InlineKeyboardButton("🕖 19:00", callback_data=f"set_once_time_{date_str}_19:00"),
                 InlineKeyboardButton("🕗 20:00", callback_data=f"set_once_time_{date_str}_20:00")],
                [InlineKeyboardButton("✏️ Jam Lain", callback_data=f"set_once_time_{date_str}_custom")],
                [InlineKeyboardButton("❌ Kembali", callback_data="add_remind_once")],
            ]
            await query.edit_message_text(
                f"📅 *{date_str}*\nPilih jam:",
                parse_mode="MarkdownV2",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
    elif data.startswith("set_once_time_"):
        parts = data.replace("set_once_time_", "").rsplit("_", 1)
        date_str = parts[0]
        time_str = parts[1]
        if time_str == "custom":
            user_reminder_state[update.effective_user.id] = {"type": "once", "date": date_str, "step": "time"}
            await query.edit_message_text(
                "✏️ *Ketik jam manual:*\nFormat: `HH:MM`\nContoh: `14:30`",
                parse_mode="MarkdownV2",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data="add_remind_once")]]),
            )
        else:
            user_reminder_state[update.effective_user.id] = {"type": "once", "date": date_str, "time": time_str, "step": "text"}
            await query.edit_message_text(
                f"📅 *{date_str}* jam *{time_str}*\n\nKetik pesan reminder:",
                parse_mode="MarkdownV2",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data="add_remind_once")]]),
            )
    elif data == "list_reminders":
        reminders = sched.get_reminders(update.effective_user.id)
        if reminders:
            lines = ["📋 *Semua Reminder*\n"]
            for r in reminders:
                rid = r['id']
                rt = escape_markdown(r['remind_at'][:16], version=2)
                rtext = escape_markdown(r['text'], version=2)
                repeat = f" \\(_{escape_markdown(r['repeat'], version=2)}_\\)" if r['repeat'] else ""
                lines.append(f"  #{rid}  {rt}{repeat}  {rtext}")
            msg = "\n".join(lines)
        else:
            msg = "Tidak ada reminder aktif\\."
        await query.edit_message_text(msg, parse_mode="MarkdownV2", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Kembali", callback_data="menu_reminder")]]))
    elif data.startswith("del_remind_"):
        rid = int(data.split("_")[-1])
        if sched.remove_reminder(rid):
            await query.answer(f"Reminder #{rid} dihapus")
            reminders = sched.get_reminders(update.effective_user.id)
            keyboard = [
                [InlineKeyboardButton("➕ Reminder Harian", callback_data="add_remind_daily")],
                [InlineKeyboardButton("➕ Reminder Sekali", callback_data="add_remind_once")],
            ]
            if reminders:
                keyboard.append([InlineKeyboardButton("📋 Lihat Semua Reminder", callback_data="list_reminders")])
                for r in reminders:
                    rid2 = r['id']
                    rtext = r['text'][:20]
                    keyboard.append([InlineKeyboardButton(f"🗑️ #{rid2} {rtext}", callback_data=f"del_remind_{rid2}")])
            keyboard.append([InlineKeyboardButton("❌ Kembali", callback_data="menu_start")])
            if reminders:
                lines = ["⏰ *Reminder Aktif*\n"]
                for r in reminders:
                    rid2 = r['id']
                    rt = escape_markdown(r['remind_at'][:16], version=2)
                    rtext = escape_markdown(r['text'], version=2)
                    repeat = f" \\(_{escape_markdown(r['repeat'], version=2)}_\\)" if r['repeat'] else ""
                    lines.append(f"  #{rid2}  {rt}{repeat}  {rtext}")
                msg = "\n".join(lines)
            else:
                msg = "⏰ *Reminder*\n\nSemua reminder sudah dihapus\\."
            await query.edit_message_text(msg, parse_mode="MarkdownV2", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.answer(f"Reminder #{rid} tidak ditemukan", show_alert=True)
    elif data == "menu_rank":
        s = storage.get_stats()
        total = s["total"]
        all_entries = storage.get_all_entries()
        xp = get_xp_progress(total)
        streak = get_streak_info(all_entries)
        bar = format_progress_bar(xp["percent"])
        rank = xp["rank"]
        next_rank = xp["next"]
        lines = [
            "╔════════════════════════╗",
            "⚔️   *HUNTER RANK STATUS*   ⚔️",
            "╚════════════════════════╝\n",
            f"{rank['emoji']} *Rank:* `{escape_markdown(rank['rank'], version=2)}` \\— {escape_markdown(rank['title'], version=2)}",
            f"📊 *Total Catatan:* `{total}`",
            f"📅 *Hari Aktif:* `{s['days']}`\n",
        ]
        if next_rank:
            lines.append(f"*Progress ke {escape_markdown(next_rank['rank'], version=2)}:*\n")
            lines.append(f"`{bar}` {xp['percent']}%")
            lines.append(f"_{xp['entries_needed']} catatan lagi ke {escape_markdown(next_rank['rank'], version=2)}_")
        else:
            lines.append("_*MAX RANK TERCAPAI\\!* 🏆_")
        if streak["streak"] > 0:
            lines.append(f"\n🔥 *Streak:* `{streak['streak']}` hari")
            if streak["milestone"]:
                m = streak["milestone"]
                lines.append(f"{m['emoji']} *Title:* {escape_markdown(m['title'], version=2)}")
        lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("_Terus catat aktivitas\\! Arise\\!_")
        msg = "\n".join(lines)
        await query.edit_message_text(msg, parse_mode="MarkdownV2", reply_markup=_menu_keyboard())
    elif data == "menu_stats":
        s = storage.get_stats()
        if s["total"] == 0:
            msg = "Belum ada catatan\\."
        else:
            msg = (
                f"📈 *Statistik Hunter*\n\n"
                f"Total catatan: {s['total']}\n"
                f"Total hari aktif: {s['days']}\n"
                f"Pertama: {escape_markdown(s['first_date'], version=2)}\n"
                f"Terakhir: {escape_markdown(s['last_date'], version=2)}"
            )
        await query.edit_message_text(msg, parse_mode="MarkdownV2", reply_markup=_menu_keyboard())
    elif data == "menu_all":
        dates = storage.get_all_dates()
        if not dates:
            msg = "Belum ada catatan\\."
        else:
            total = storage.get_entry_count()
            lines = [f"🗂️ *Arsip Harian \\({total} catatan\\)*\n"]
            for d, count in dates:
                lines.append(f"  {escape_markdown(d, version=2)}  \\({count}\\)")
            msg = "\n".join(lines)
        await query.edit_message_text(msg, parse_mode="MarkdownV2", reply_markup=_menu_keyboard())
    elif data == "menu_clear":
        entries = storage.get_today()
        if not entries:
            await query.edit_message_text(
                "🗑️ *Hapus Log*\n\nTidak ada catatan hari ini\\.",
                parse_mode="MarkdownV2",
                reply_markup=_menu_keyboard()
            )
            return
        delete_selections[update.effective_user.id] = {"selected": set(), "entries": entries}
        await _show_delete_list(query, entries, set(), update.effective_user.id)
    elif data.startswith("toggle_del_"):
        eid = int(data.split("_")[-1])
        uid = update.effective_user.id
        sel = delete_selections.get(uid, {"selected": set(), "entries": storage.get_today()})
        if eid in sel["selected"]:
            sel["selected"].discard(eid)
        else:
            sel["selected"].add(eid)
        delete_selections[uid] = sel
        await _show_delete_list(query, sel["entries"], sel["selected"], uid)
    elif data == "delete_selected":
        uid = update.effective_user.id
        sel = delete_selections.pop(uid, None)
        if not sel or not sel["selected"]:
            await query.edit_message_text(
                "Tidak ada log yang dipilih\\.",
                parse_mode="MarkdownV2",
                reply_markup=_menu_keyboard()
            )
            return
        count = 0
        for eid in sel["selected"]:
            if storage.delete_entry(eid):
                count += 1
        await query.edit_message_text(
            f"✅ *{count} log berhasil dihapus\\!*",
            parse_mode="MarkdownV2",
            reply_markup=_menu_keyboard()
        )
    elif data == "delete_all_today":
        uid = update.effective_user.id
        delete_selections.pop(uid, None)
        storage.clear_all()
        await query.edit_message_text(
            "✅ *Semua log berhasil dihapus\\!* Data jurnal telah dibersihkan\\.",
            parse_mode="MarkdownV2",
            reply_markup=_menu_keyboard()
        )
    elif data == "menu_restart":
        restart_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".restart_chat")
        with open(restart_file, "w") as f:
            f.write(str(update.effective_chat.id))
        await query.edit_message_text("🔄 *Memulai ulang bot\\.\\.\\. Arise\\!*", parse_mode="MarkdownV2")
        await asyncio.sleep(1)
        import subprocess, sys
        subprocess.Popen([sys.executable] + sys.argv, cwd=os.path.dirname(os.path.abspath(__file__)) + "/..")
        os._exit(0)
    elif data == "export_today":
        print(f"[DEBUG] export_today callback received")
        today = date.today().isoformat()
        await _generate_and_send_pdf(query, start_date=today, end_date=today)
    elif data == "export_week":
        print(f"[DEBUG] export_week callback received")
        week_ago = (date.today() - timedelta(days=7)).isoformat()
        today = date.today().isoformat()
        await _generate_and_send_pdf(query, start_date=week_ago, end_date=today)
    elif data == "export_month":
        print(f"[DEBUG] export_month callback received")
        first_day = date.today().replace(day=1).isoformat()
        today = date.today().isoformat()
        await _generate_and_send_pdf(query, start_date=first_day, end_date=today)
    elif data == "export_all":
        print(f"[DEBUG] export_all callback received")
        await _generate_and_send_pdf(query)
    elif data == "export_custom":
        print(f"[DEBUG] export_custom callback received")
        await query.edit_message_text(
            "✏️ *Custom Date Range*\n\nKetik:\n`/export YYYY\-MM\-DD YYYY\-MM\-DD`\n\nContoh:\n`/export 2026\-06\-01 2026\-06\-15`",
            parse_mode="MarkdownV2",
            reply_markup=_menu_keyboard(),
        )
    elif data == "menu_help":
        text = (
            "⚔️ *SoloLeveling Journal* ⚔️\n\n"
            "*Commands:*\n"
            "`/start` — Menu utama\n"
            "`/rank` — Cek Rank Hunter kamu\n"
            "`/agenda` — Tampilkan agenda hari ini\n"
            "`/log \\<teks\\>` — Catat kegiatan manual\n"
            "`/today` — Lihat catatan hari ini\n"
            "`/yesterday` — Lihat catatan kemarin\n"
            "`/date YYYY\-MM\-DD` — Catatan tanggal tertentu\n"
            "`/search \\<kata\\>` — Cari catatan lama\n"
            "`/all` — Tampilkan arsip tanggal\n"
            "`/stats` — Statistik Hunter\n"
            "`/rank` — Cek Rank Hunter\n"
            "`/export` — Export jurnal ke PDF\n"
            "`/export YYYY\-MM\-DD YYYY\-MM\-DD` — Export periode tertentu\n"
            "`/del \\<id\\>` — Hapus catatan\n"
            "`/clear` — Hapus semua log catatan\n"
            "`/restart` — Memulai ulang bot (refresh)\n"
            "`/remind \\<HH:MM\\> \\<pesan\\>` — Reminder harian\n"
            "`/remindat \\<YYYY\-MM\-DD HH:MM\\> \\<pesan\\>` — Reminder sekali\n"
            "`/reminders` — Daftar reminder aktif\n"
            "`/unremind \\<id\\>` — Hapus reminder\n\n"
            "Atau kirim pesan langsung untuk mencatat log harian secara instan\\."
        )
        await query.edit_message_text(text, parse_mode="MarkdownV2", reply_markup=_menu_keyboard())


async def cmd_log(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update):
        return
    text = " ".join(ctx.args)
    if not text:
        await update.message.reply_text("Gunakan: /log \\<teks kegiatan\\>", parse_mode="MarkdownV2")
        return
    
    chat_id = update.effective_chat.id
    safe_delete_message(update.message)

    old_msg = last_bot_messages.get(chat_id)
    if old_msg:
        try:
            await old_msg.delete()
        except Exception:
            pass

    entry = storage.add_entry(text)
    msg_text = f"✅ *Tersimpan*\n{_fmt_entry(entry)}"
    await _send_and_auto_delete(update.message, msg_text)


async def cmd_agenda(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update):
        return
    safe_delete_message(update.message)
    msg = get_agenda_text(update.effective_user.id)
    await update.message.reply_text(msg, parse_mode="MarkdownV2", reply_markup=_menu_keyboard())


async def cmd_today(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update):
        return
    safe_delete_message(update.message)
    entries = storage.get_today()
    today_str = date.today().isoformat()
    msg = _fmt_entries(entries, f"Hari Ini \\({today_str}\\)")
    if len(msg) > 4000:
        msg = msg[:4000] + "\n\n... \(terlalu panjang\)"
    await update.message.reply_text(msg, parse_mode="MarkdownV2", reply_markup=_menu_keyboard())


async def cmd_yesterday(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update):
        return
    safe_delete_message(update.message)
    entries = storage.get_yesterday()
    yesterday_str = (date.today() - timedelta(days=1)).isoformat()
    msg = _fmt_entries(entries, f"Kemarin ({yesterday_str})")
    await update.message.reply_text(msg, parse_mode="MarkdownV2", reply_markup=_menu_keyboard())


async def cmd_date(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update):
        return
    safe_delete_message(update.message)
    d = " ".join(ctx.args)
    if not d:
        await update.message.reply_text("Gunakan: /date YYYY\-MM\-DD")
        return
    entries = storage.get_by_date(d)
    msg = _fmt_entries(entries, f"Catatan \\({d}\\)")
    await update.message.reply_text(msg, parse_mode="MarkdownV2", reply_markup=_menu_keyboard())


async def cmd_search(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update):
        return
    safe_delete_message(update.message)
    kw = " ".join(ctx.args)
    if not kw:
        await update.message.reply_text("Gunakan: /search \\<kata kunci\\>", parse_mode="MarkdownV2")
        return
    results = storage.search(kw)
    if not results:
        await update.message.reply_text(f"Tidak ditemukan catatan dengan kata: {kw}")
        return
    msg = _fmt_entries(results, f"Hasil pencarian: {kw} ({len(results)})")
    if len(msg) > 4000:
        msg = msg[:4000] + "\n\n... \(terlalu panjang\)"
    await update.message.reply_text(msg, parse_mode="MarkdownV2", reply_markup=_menu_keyboard())


async def cmd_all(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update):
        return
    safe_delete_message(update.message)
    dates = storage.get_all_dates()
    if not dates:
        await update.message.reply_text("Belum ada catatan\\.", parse_mode="MarkdownV2")
        return
    total = storage.get_entry_count()
    lines = [f"🗂️ *Semua Tanggal \\({total} catatan\\)*\n"]
    for d, count in dates:
        lines.append(f"  {escape_markdown(d, version=2)}  \\({count}\\)")
    msg = "\n".join(lines)
    await update.message.reply_text(msg, parse_mode="MarkdownV2", reply_markup=_menu_keyboard())


async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update):
        return
    safe_delete_message(update.message)
    s = storage.get_stats()
    if s["total"] == 0:
        await update.message.reply_text("Belum ada catatan\\.", parse_mode="MarkdownV2")
        return
    msg = (
        f"📈 *Statistik Hunter*\n\n"
        f"Total catatan: {s['total']}\n"
        f"Total hari aktif: {s['days']}\n"
        f"Pertama: {escape_markdown(s['first_date'], version=2)}\n"
        f"Terakhir: {escape_markdown(s['last_date'], version=2)}"
    )
    await update.message.reply_text(msg, parse_mode="MarkdownV2", reply_markup=_menu_keyboard())


async def cmd_del(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update):
        return
    safe_delete_message(update.message)
    try:
        eid = int(" ".join(ctx.args))
    except (ValueError, IndexError):
        await update.message.reply_text("Gunakan: /del \\<id catatan\\>", parse_mode="MarkdownV2")
        return
    if storage.delete_entry(eid):
        await update.message.reply_text(f"Catatan #{eid} deleted.")
    else:
        await update.message.reply_text(f"Catatan #{eid} tidak ditemukan.")


async def cmd_clear(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update):
        return
    safe_delete_message(update.message)
    entries = storage.get_today()
    if not entries:
        await update.message.reply_text(
            "🗑️ *Hapus Log*\n\nTidak ada catatan hari ini\\.",
            parse_mode="MarkdownV2",
            reply_markup=_menu_keyboard()
        )
        return
    delete_selections[update.effective_user.id] = {"selected": set(), "entries": entries}
    lines = [f"🗑️ *Hapus Log* \\({len(entries)} catatan hari ini\\)\n"]
    lines.append("_Pilih log yang ingin dihapus, lalu tekan *Hapus Terpilih*_\n")
    for e in entries:
        t = escape_markdown(e["time"][:5], version=2)
        txt = escape_markdown(e["text"], version=2)
        lines.append(f"⬜ `#{e['id']}` `[{t}]` {txt}")
    msg = "\n".join(lines)

    keyboard = []
    for e in entries:
        keyboard.append([InlineKeyboardButton(f"⬜ #{e['id']} {e['time'][:5]}", callback_data=f"toggle_del_{e['id']}")])
    btn_row = [
        InlineKeyboardButton("🗑️ Hapus Semua", callback_data="delete_all_today"),
        InlineKeyboardButton("❌ Batal", callback_data="menu_start"),
    ]
    keyboard.append(btn_row)

    await update.message.reply_text(msg, parse_mode="MarkdownV2", reply_markup=InlineKeyboardMarkup(keyboard))


async def cmd_restart(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update):
        return
    safe_delete_message(update.message)
    restart_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".restart_chat")
    with open(restart_file, "w") as f:
        f.write(str(update.effective_chat.id))
    await update.message.reply_text("🔄 *Memulai ulang bot\\.\\.\\. Arise\\!*", parse_mode="MarkdownV2")
    await asyncio.sleep(1)
    import subprocess, sys
    subprocess.Popen([sys.executable] + sys.argv, cwd=os.path.dirname(os.path.abspath(__file__)) + "/..")
    os._exit(0)


async def cmd_remind(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update):
        return
    args = " ".join(ctx.args)
    if not args:
        await update.message.reply_text(
            "Gunakan: /remind \\<HH:MM\\> \\<pesan\\>\nContoh: `/remind 09:00 Minum kopi`",
            parse_mode="MarkdownV2",
        )
        return
    match = re.match(r"^(\d{1,2}):(\d{2})\s+(.+)", args)
    if not match:
        await update.message.reply_text("Format salah. Gunakan: `/remind 09:00 pesan`", parse_mode="MarkdownV2")
        return
    hour, minute, text = int(match.group(1)), int(match.group(2)), match.group(3)
    now = datetime.now()
    remind_at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if remind_at <= now:
        remind_at += timedelta(days=1)
    entry = sched.add_reminder(
        bot=ctx.bot,
        chat_id=update.effective_user.id,
        text=text,
        remind_at=remind_at,
        repeat="daily",
    )
    rt = remind_at.strftime("%H:%M")
    await update.message.reply_text(
        f"✅ Reminder harian diatur setiap {rt}\n_{escape_markdown(text, version=2)}_",
        parse_mode="MarkdownV2",
        reply_markup=_menu_keyboard(),
    )


async def cmd_remindat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update):
        return
    args = " ".join(ctx.args)
    if not args:
        await update.message.reply_text(
            "Gunakan: /remindat \\<YYYY\-MM\-DD HH:MM\\> \\<pesan\\>\n"
            "Contoh: `/remindat 2026\\-06\\-16 14:30 Meeting`",
            parse_mode="MarkdownV2",
        )
        return
    match = re.match(r"^(\d{4}-\d{2}-\d{2})\s+(\d{1,2}):(\d{2})\s+(.+)", args)
    if not match:
        await update.message.reply_text("Format salah.")
        return
    date_str, hour, minute, text = match.group(1), int(match.group(2)), int(match.group(3)), match.group(4)
    try:
        remind_at = datetime.strptime(f"{date_str} {hour}:{minute}", "%Y-%m-%d %H:%M")
    except ValueError:
        await update.message.reply_text("Tanggal tidak valid.")
        return
    entry = sched.add_reminder(
        bot=ctx.bot,
        chat_id=update.effective_user.id,
        text=text,
        remind_at=remind_at,
        repeat=None,
    )
    rt = remind_at.strftime("%Y-%m-%d %H:%M")
    await update.message.reply_text(
        f"✅ Reminder diatur pada {rt}\n_{escape_markdown(text, version=2)}_",
        parse_mode="MarkdownV2",
        reply_markup=_menu_keyboard(),
    )


async def cmd_reminders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update):
        return
    reminders = sched.get_reminders(update.effective_user.id)
    if not reminders:
        await update.message.reply_text("Tidak ada reminder aktif.")
        return
    lines = ["⏰ *Reminder Aktif*\n"]
    for r in reminders:
        rid = r['id']
        rt = escape_markdown(r['remind_at'][:16], version=2)
        rtext = escape_markdown(r['text'], version=2)
        repeat = f" (_{escape_markdown(r['repeat'], version=2)}_)" if r['repeat'] else ""
        lines.append(f"  #{rid}  {rt}{repeat}  {rtext}")
    lines.append("\nGunakan `/unremind \\<id\\>` untuk menghapus")
    await update.message.reply_text("\n".join(lines), parse_mode="MarkdownV2")


async def cmd_unremind(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update):
        return
    try:
        rid = int(" ".join(ctx.args))
    except (ValueError, IndexError):
        await update.message.reply_text("Gunakan: /unremind \\<id\\>", parse_mode="MarkdownV2")
        return
    if sched.remove_reminder(rid):
        await update.message.reply_text(f"Reminder #{rid} dihapus.")
    else:
        await update.message.reply_text(f"Reminder #{rid} tidak ditemukan.")


async def cmd_export(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update):
        return
    safe_delete_message(update.message)

    args = " ".join(ctx.args)
    if args:
        match = re.match(r"^(\d{4}\-\d{2}\-\d{2})\s+(\d{4}\-\d{2}\-\d{2})$", args)
        if match:
            start_date = match.group(1)
            end_date = match.group(2)
            msg = await update.message.reply_text("📄 *Generating PDF report\\.\\.\\.*", parse_mode="MarkdownV2")
            await _generate_and_send_pdf_custom(update.message, start_date, end_date)
            return

    keyboard = [
        [InlineKeyboardButton("📅 Hari Ini", callback_data="export_today")],
        [InlineKeyboardButton("📆 7 Hari Terakhir", callback_data="export_week")],
        [InlineKeyboardButton("📋 Bulan Ini", callback_data="export_month")],
        [InlineKeyboardButton("📚 Semua Data", callback_data="export_all")],
        [InlineKeyboardButton("✏️ Custom Date", callback_data="export_custom")],
        [InlineKeyboardButton("❌ Batal", callback_data="menu_start")],
    ]
    await update.message.reply_text(
        "📄 *Export Jurnal ke PDF*\n\nPilih periode yang ingin di\\-export\\:",
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def _generate_and_send_pdf_custom(message, start_date=None, end_date=None):
    try:
        today = date.today().isoformat()
        output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), f"journal_{today}.pdf")
        generate_pdf(start_date=start_date, end_date=end_date, output_path=output_path)

        caption = "Journal Report\n\n"
        if start_date and end_date:
            caption += f"Period: {start_date} to {end_date}\n"
        caption += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        with open(output_path, "rb") as f:
            await message.reply_document(
                document=f,
                filename=f"journal_{today}.pdf",
                caption=caption,
            )

        os.remove(output_path)

    except Exception as e:
        await message.reply_text(f"❌ Gagal generate PDF: {str(e)}")


async def _generate_and_send_pdf(query, start_date=None, end_date=None):
    await query.edit_message_text("📄 *Generating PDF report\\.\\.\\.*", parse_mode="MarkdownV2")

    try:
        today = date.today().isoformat()
        output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), f"journal_{today}.pdf")
        print(f"[EXPORT] Generating PDF: {start_date} to {end_date}")
        generate_pdf(start_date=start_date, end_date=end_date, output_path=output_path)
        print(f"[EXPORT] PDF generated: {output_path}")

        caption = "Journal Report\n\n"
        if start_date and end_date:
            caption += f"Period: {start_date} to {end_date}\n"
        elif start_date:
            caption += f"From: {start_date}\n"
        elif end_date:
            caption += f"Until: {end_date}\n"
        else:
            caption += "All entries\n"
        caption += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        with open(output_path, "rb") as f:
            await query.message.reply_document(
                document=f,
                filename=f"journal_{today}.pdf",
                caption=caption,
            )

        os.remove(output_path)
        try:
            await query.delete_message()
        except Exception:
            pass

    except Exception as e:
        print(f"[EXPORT] Error: {e}")
        try:
            await query.edit_message_text(f"❌ Gagal generate PDF: {str(e)}")
        except Exception:
            pass


async def cmd_rank(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update):
        return
    safe_delete_message(update.message)
    s = storage.get_stats()
    total = s["total"]
    all_entries = storage.get_all_entries()
    xp = get_xp_progress(total)
    streak = get_streak_info(all_entries)
    bar = format_progress_bar(xp["percent"])

    rank = xp["rank"]
    next_rank = xp["next"]

    lines = [
        "╔════════════════════════╗",
        "⚔️   *HUNTER RANK STATUS*   ⚔️",
        "╚════════════════════════╝\n",
        f"{rank['emoji']} *Rank:* `{escape_markdown(rank['rank'], version=2)}` \\— {escape_markdown(rank['title'], version=2)}",
        f"📊 *Total Catatan:* `{total}`",
        f"📅 *Hari Aktif:* `{s['days']}`\n",
    ]

    if next_rank:
        lines.append(f"*Progress ke {escape_markdown(next_rank['rank'], version=2)}:*\n")
        lines.append(f"`{bar}` {xp['percent']}%")
        lines.append(f"_{xp['entries_needed']} catatan lagi ke {escape_markdown(next_rank['rank'], version=2)}_")
    else:
        lines.append("_*MAX RANK TERCAPAI\\!* 🏆_")

    if streak["streak"] > 0:
        lines.append(f"\n🔥 *Streak:* `{streak['streak']}` hari")
        if streak["milestone"]:
            m = streak["milestone"]
            lines.append(f"{m['emoji']} *Title:* {escape_markdown(m['title'], version=2)}")

    lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("_Terus catat aktivitas\\! Arise\\!_")

    msg = "\n".join(lines)
    await update.message.reply_text(msg, parse_mode="MarkdownV2", reply_markup=_menu_keyboard())


async def auto_log(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update):
        return
    text = update.message.text.strip()
    if not text:
        return

    uid = update.effective_user.id
    chat_id = update.effective_chat.id
    track_user(chat_id)

    if uid in user_reminder_state:
        state = user_reminder_state.pop(uid)
        step = state["step"]

        if state["type"] == "daily":
            if step == "time":
                if not re.match(r"^\d{1,2}:\d{2}$", text):
                    await update.message.reply_text("Format jam salah. Gunakan: HH:MM\nContoh: 09:30")
                    return
                state["time"] = text
                state["step"] = "text"
                user_reminder_state[uid] = state
                await update.message.reply_text(f"⏰ Reminder harian jam {text}\n\nKetik pesan reminder:")
                return
            elif step == "text":
                hour, minute = map(int, state["time"].split(":"))
                now = datetime.now()
                remind_at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if remind_at <= now:
                    remind_at += timedelta(days=1)
                sched.add_reminder(
                    bot=ctx.bot,
                    chat_id=chat_id,
                    text=text,
                    remind_at=remind_at,
                    repeat="daily",
                )
                await _send_and_auto_delete(update.message, f"✅ Reminder harian jam {state['time']} diatur\\!\nPesan: {text}")
                return

        elif state["type"] == "once":
            if step == "date":
                if not re.match(r"^\d{4}-\d{2}-\d{2}$", text):
                    await update.message.reply_text("Format tanggal salah. Gunakan: YYYY-MM-DD\nContoh: 2026-06-20")
                    return
                state["date"] = text
                state["step"] = "time"
                user_reminder_state[uid] = state
                await update.message.reply_text(f"📅 Tanggal: {text}\n\nKetik jam (HH:MM):")
                return
            elif step == "time":
                if not re.match(r"^\d{1,2}:\d{2}$", text):
                    await update.message.reply_text("Format jam salah. Gunakan: HH:MM\nContoh: 14:30")
                    return
                state["time"] = text
                state["step"] = "text"
                user_reminder_state[uid] = state
                await update.message.reply_text(f"📅 {state['date']} jam {text}\n\nKetik pesan reminder:")
                return
            elif step == "text":
                try:
                    remind_at = datetime.strptime(f"{state['date']} {state['time']}", "%Y-%m-%d %H:%M")
                except ValueError:
                    await update.message.reply_text("Tanggal atau jam tidak valid.")
                    return
                sched.add_reminder(
                    bot=ctx.bot,
                    chat_id=chat_id,
                    text=text,
                    remind_at=remind_at,
                    repeat=None,
                )
                await _send_and_auto_delete(update.message, f"✅ Reminder sekali diatur\\!\n📅 {state['date']} {state['time']}\nPesan: {text}")
                return

    safe_delete_message(update.message)

    old_msg = last_bot_messages.get(chat_id)
    if old_msg:
        try:
            await old_msg.delete()
        except Exception:
            pass

    entry = storage.add_entry(text)
    msg_text = f"✅ *Tersimpan*\n{_fmt_entry(entry)}"
    await _send_and_auto_delete(update.message, msg_text)


def get_handlers():
    return [
        CommandHandler("start", start),
        CommandHandler("agenda", cmd_agenda),
        CommandHandler("log", cmd_log),
        CommandHandler("today", cmd_today),
        CommandHandler("yesterday", cmd_yesterday),
        CommandHandler("date", cmd_date),
        CommandHandler("search", cmd_search),
        CommandHandler("all", cmd_all),
        CommandHandler("stats", cmd_stats),
        CommandHandler("rank", cmd_rank),
        CommandHandler("export", cmd_export),
        CommandHandler("del", cmd_del),
        CommandHandler("clear", cmd_clear),
        CommandHandler("restart", cmd_restart),
        CommandHandler("remind", cmd_remind),
        CommandHandler("remindat", cmd_remindat),
        CommandHandler("reminders", cmd_reminders),
        CommandHandler("unremind", cmd_unremind),
        CallbackQueryHandler(menu_callback, pattern="^(menu_|export_|add_remind_|set_daily_|set_once_|del_remind_|list_reminders)"),
        MessageHandler(filters.TEXT & ~filters.COMMAND, auto_log),
    ]
