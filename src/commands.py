import os
import re
import asyncio
from datetime import date, datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown

from src import storage
from src import scheduler as sched
from src.ranks import get_rank, get_xp_progress, get_streak_info, format_progress_bar
from src.pdf_export import generate_pdf
from src.user_tracker import track_user
from src.helpers import (
    OWNER_ID, _is_owner, safe_delete_message, _fmt_entry, _fmt_entries,
    _menu_keyboard, _section_keyboard, _send_and_auto_delete,
    _delete_all_bot_messages, last_bot_messages, bot_message_history,
    user_reminder_state
)


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update):
        await update.message.reply_text("⛔ Bot ini pribadi.")
        return
    track_user(update.effective_chat.id)
    chat_id = update.effective_chat.id

    safe_delete_message(update.message)
    await _delete_all_bot_messages(chat_id, ctx)

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
    msg = await update.message.reply_text(text, parse_mode="MarkdownV2", reply_markup=_menu_keyboard())
    last_bot_messages[chat_id] = msg


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
    
    if chat_id not in bot_message_history:
        bot_message_history[chat_id] = []
    
    try:
        msg = await ctx.bot.send_message(chat_id=chat_id, text=msg_text, parse_mode="MarkdownV2")
        bot_message_history[chat_id].append(msg.message_id)
        asyncio.create_task(_auto_delete_message(ctx.bot, chat_id, msg.message_id, 3))
    except Exception:
        pass


async def _auto_delete_message(bot, chat_id, message_id, delay):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        if chat_id in bot_message_history and message_id in bot_message_history[chat_id]:
            bot_message_history[chat_id].remove(message_id)
    except Exception:
        pass


async def cmd_agenda(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update):
        return
    safe_delete_message(update.message)
    from src.callbacks import get_agenda_text
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
    msg = _fmt_entries(entries, f"Kemarin \\({yesterday_str}\\)")
    await update.message.reply_text(msg, parse_mode="MarkdownV2", reply_markup=_menu_keyboard())


async def cmd_date(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update):
        return
    safe_delete_message(update.message)
    d = " ".join(ctx.args)
    if not d:
        await update.message.reply_text("Gunakan: /date YYYY\-MM\-DD", parse_mode="MarkdownV2")
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
    msg = _fmt_entries(results, f"Hasil pencarian: {kw} \\({len(results)}\\)")
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
    user_reminder_state[update.effective_user.id] = {"selected": set(), "entries": entries}
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
    sched.add_reminder(
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
            "Contoh: `/remindat 2026\-06\-16 14:30 Meeting`",
            parse_mode="MarkdownV2",
        )
        return
    match = re.match(r"^(\d{4}\-\d{2}\-\d{2})\s+(\d{1,2}):(\d{2})\s+(.+)", args)
    if not match:
        await update.message.reply_text("Format salah.")
        return
    date_str, hour, minute, text = match.group(1), int(match.group(2)), int(match.group(3)), match.group(4)
    try:
        remind_at = datetime.strptime(f"{date_str} {hour}:{minute}", "%Y-%m-%d %H:%M")
    except ValueError:
        await update.message.reply_text("Tanggal tidak valid.")
        return
    sched.add_reminder(
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
        repeat = f" \\(_{escape_markdown(r['repeat'], version=2)}_\\)" if r['repeat'] else ""
        lines.append(f"  \\#{rid}  {rt}{repeat}  {rtext}")
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
    
    if chat_id not in bot_message_history:
        bot_message_history[chat_id] = []
    
    try:
        msg = await ctx.bot.send_message(chat_id=chat_id, text=msg_text, parse_mode="MarkdownV2")
        bot_message_history[chat_id].append(msg.message_id)
        asyncio.create_task(_auto_delete_message(ctx.bot, chat_id, msg.message_id, 3))
    except Exception:
        pass
