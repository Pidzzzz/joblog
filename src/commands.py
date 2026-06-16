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
    user_reminder_state, bot_stats, estimate_tokens, append_to_history,
    remove_from_history, _send_menu
)
from src.image_generator import (
    generate_welcome_card, generate_status_card, generate_stats_card,
    generate_agenda_card
)


def _track_command(update: Update):
    bot_stats["messages_received"] += 1
    bot_stats["commands_used"] += 1
    if bot_stats["start_time"] is None:
        bot_stats["start_time"] = datetime.now()
    if update.message:
        append_to_history(update.effective_chat.id, update.message.message_id)


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    _track_command(update)
    if not _is_owner(update):
        await update.message.reply_text("⛔ Bot ini pribadi.")
        return
    track_user(update.effective_chat.id)
    chat_id = update.effective_chat.id

    safe_delete_message(update.message)

    s = storage.get_stats()
    xp = get_xp_progress(s["total"])
    rank = xp["rank"]
    
    photo_bytes = generate_welcome_card(
        hunter_name=update.effective_user.first_name,
        rank_letter=rank["rank"],
        rank_title=rank["title"],
        total_entries=s["total"],
        active_days=s["days"]
    )
    
    caption = "*SoloLeveling Journal* \\— Main System"
    await _send_menu(
        chat_id=chat_id,
        bot=ctx.bot,
        text=caption,
        photo=photo_bytes,
        reply_markup=_menu_keyboard()
    )


async def cmd_log(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    _track_command(update)
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
    
    try:
        msg = await ctx.bot.send_message(chat_id=chat_id, text=msg_text, parse_mode="MarkdownV2")
        append_to_history(chat_id, msg.message_id)
        bot_stats["messages_sent"] += 1
        bot_stats["tokens_used"] += estimate_tokens(msg_text)
        asyncio.create_task(_auto_delete_message(ctx.bot, chat_id, msg.message_id, 3))
    except Exception:
        pass


async def _auto_delete_message(bot, chat_id, message_id, delay):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        remove_from_history(chat_id, message_id)
    except Exception:
        pass


async def cmd_agenda(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    _track_command(update)
    if not _is_owner(update):
        return
    safe_delete_message(update.message)
    chat_id = update.effective_chat.id
    
    logs = storage.get_today()
    all_reminders = sched.get_reminders(chat_id)
    today_str = date.today().isoformat()
    
    today_reminders = []
    for r in all_reminders:
        if r.get("repeat") == "daily":
            today_reminders.append(r)
        else:
            r_date = r.get("remind_at", "").split("T")[0]
            if r_date == today_str:
                today_reminders.append(r)
                
    photo_bytes = generate_agenda_card(
        date_str=today_str,
        active_quests=today_reminders,
        cleared_quests=logs
    )
    
    caption = "*SoloLeveling Journal* \\— Daily Quest Board"
    await _send_menu(
        chat_id=chat_id,
        bot=ctx.bot,
        text=caption,
        photo=photo_bytes,
        reply_markup=_menu_keyboard()
    )


async def cmd_today(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    _track_command(update)
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
    _track_command(update)
    if not _is_owner(update):
        return
    safe_delete_message(update.message)
    entries = storage.get_yesterday()
    yesterday_str = (date.today() - timedelta(days=1)).isoformat()
    msg = _fmt_entries(entries, f"Kemarin \\({yesterday_str}\\)")
    await update.message.reply_text(msg, parse_mode="MarkdownV2", reply_markup=_menu_keyboard())


async def cmd_date(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    _track_command(update)
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
    _track_command(update)
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
    _track_command(update)
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
    _track_command(update)
    if not _is_owner(update):
        return
    safe_delete_message(update.message)
    chat_id = update.effective_chat.id
    s = storage.get_stats()
    
    photo_bytes = generate_stats_card(
        total_entries=s["total"],
        active_days=s["days"],
        first_date=s["first_date"],
        last_date=s["last_date"]
    )
    
    caption = "*SoloLeveling Journal* \\— Hunter Statistics"
    await _send_menu(
        chat_id=chat_id,
        bot=ctx.bot,
        text=caption,
        photo=photo_bytes,
        reply_markup=_menu_keyboard()
    )


async def cmd_del(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    _track_command(update)
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
    _track_command(update)
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
    _track_command(update)
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
    _track_command(update)
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
    _track_command(update)
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
    _track_command(update)
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
    _track_command(update)
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
    _track_command(update)
    if not _is_owner(update):
        return
    safe_delete_message(update.message)
    chat_id = update.effective_chat.id
    
    s = storage.get_stats()
    total = s["total"]
    all_entries = storage.get_all_entries()
    xp = get_xp_progress(total)
    streak = get_streak_info(all_entries)
    rank = xp["rank"]
    
    streak_title = streak["milestone"]["title"] if streak["milestone"] else "Novice Hunter"
    
    photo_bytes = generate_status_card(
        hunter_name=update.effective_user.first_name,
        rank_letter=rank["rank"],
        rank_title=rank["title"],
        xp_percent=xp["percent"],
        streak_days=streak["streak"],
        streak_title=streak_title,
        total_entries=total,
        active_days=s["days"]
    )
    
    caption = "*SoloLeveling Journal* \\— Hunter Status"
    await _send_menu(
        chat_id=chat_id,
        bot=ctx.bot,
        text=caption,
        photo=photo_bytes,
        reply_markup=_menu_keyboard()
    )


async def cmd_ai(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    _track_command(update)
    if not _is_owner(update):
        return
    safe_delete_message(update.message)
    
    if bot_stats["start_time"] is None:
        bot_stats["start_time"] = datetime.now()
    
    uptime = datetime.now() - bot_stats["start_time"]
    hours = int(uptime.total_seconds() // 3600)
    minutes = int((uptime.total_seconds() % 3600) // 60)
    seconds = int(uptime.total_seconds() % 60)
    
    total_api_calls = bot_stats["messages_received"] + bot_stats["messages_sent"]
    
    text = (
        "╔════════════════════════╗\n"
        "🤖   *AI SYSTEM INFO*   🤖\n"
        "╚════════════════════════╝\n\n"
        f"*Model:* `mimo\\-auto`\n"
        f"*Provider:* `Xiaomi MiMo Team`\n"
        f"*Framework:* `python\\-telegram\\-bot 22\\.8`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🛠️ *AI Assistants Used:*\n"
        "  • `MiMoCode` \\(Xiaomi MiMo Team\\)\n"
        "  • `Antigravity` \\(Google DeepMind Team\\)\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 *Statistik Penggunaan:*\n\n"
        f"  📨 Pesan diterima: `{bot_stats['messages_received']}`\n"
        f"  📤 Pesan dikirim: `{bot_stats['messages_sent']}`\n"
        f"  ⚡ Commands dipanggil: `{bot_stats['commands_used']}`\n"
        f"  🔘 Callbacks ditangani: `{bot_stats['callbacks_handled']}`\n"
        f"  🔄 Total API calls: `{total_api_calls}`\n"
        f"  🎯 Token terpakai: `{bot_stats['tokens_used']}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱️ *Uptime:* `{hours}j {minutes}m {seconds}s`\n\n"
        "_Dibuat menggunakan asisten AI MiMoCode & Antigravity_"
    )
    
    await update.message.reply_text(text, parse_mode="MarkdownV2", reply_markup=_menu_keyboard())


async def cmd_export(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    _track_command(update)
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
    if update.message:
        append_to_history(update.effective_chat.id, update.message.message_id)
    text = update.message.text.strip()
    if not text:
        return

    uid = update.effective_user.id
    chat_id = update.effective_chat.id
    track_user(chat_id)
    bot_stats["messages_received"] += 1

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

    entry = storage.add_entry(text)
    msg_text = f"✅ *Tersimpan*\n{_fmt_entry(entry)}"
    
    try:
        msg = await ctx.bot.send_message(chat_id=chat_id, text=msg_text, parse_mode="MarkdownV2")
        append_to_history(chat_id, msg.message_id)
        asyncio.create_task(_auto_delete_message(ctx.bot, chat_id, msg.message_id, 3))
    except Exception:
        pass


async def fetch_github_projects():
    import httpx
    url = "https://api.github.com/users/Pidzzzz/repos"
    headers = {"User-Agent": "python-telegram-bot"}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
    return []


async def cmd_projects(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    _track_command(update)
    if not _is_owner(update):
        return
    safe_delete_message(update.message)
    
    loading_msg = await update.message.reply_text("⏳ *Mengambil data proyek dari GitHub\\.\\.\\.*", parse_mode="MarkdownV2")
    
    try:
        repos = await fetch_github_projects()
        if not repos:
            await loading_msg.edit_text("❌ *Gagal mengambil data proyek atau tidak ada proyek\\.*", parse_mode="MarkdownV2")
            return
            
        lines = [
            "╔════════════════════════╗",
            "🐙   *GITHUB REPOSITORIES*   🐙",
            "╚════════════════════════╝\n",
        ]
        
        for repo in repos:
            name = escape_markdown(repo["name"], version=2)
            desc = escape_markdown(repo["description"] or "Tidak ada deskripsi", version=2)
            lang = escape_markdown(repo["language"] or "Other", version=2)
            stars = repo["stargazers_count"]
            url = repo["html_url"].replace("\\", "\\\\").replace(")", "\\)")
            
            lines.append(
                f"📁 *{name}* \\({lang}\\)\n"
                f"📝 {desc}\n"
                f"⭐ Stars: `{stars}`\n"
                f"🔗 [Tautan Repositori]({url})\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
            
        msg_text = "\n".join(lines)
        if len(msg_text) > 4000:
            msg_text = msg_text[:4000] + "\n\n\\.\\.\\. \\(terlalu banyak proyek\\)"
            
        await loading_msg.edit_text(msg_text, parse_mode="MarkdownV2", disable_web_page_preview=True, reply_markup=_menu_keyboard())
    except Exception as e:
        await loading_msg.edit_text(f"❌ *Error:* `{escape_markdown(str(e), version=2)}`", parse_mode="MarkdownV2")


async def analyze_food_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    import html
    import base64
    import httpx
    
    _track_command(update)
    if not _is_owner(update):
        return
    
    chat_id = update.effective_chat.id
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        msg = await update.message.reply_html(
            "❌ <b>API Key Gemini belum diatur!</b>\n\n"
            "Silakan dapatkan API Key gratis di <code>https://aistudio.google.com/</code> "
            "lalu tambahkan baris berikut di file <code>.env</code>:\n"
            "<code>GEMINI_API_KEY=key_anda</code>\n\n"
            "Setelah ditambahkan, bot akan otomatis restart dan siap digunakan.",
            reply_markup=_menu_keyboard()
        )
        append_to_history(chat_id, msg.message_id)
        return

    loading_msg = await update.message.reply_html("⏳ <b>Menganalisis foto makanan dengan AI...</b>")
    append_to_history(chat_id, loading_msg.message_id)
    
    try:
        photo = update.message.photo[-1]
        photo_file = await photo.get_file()
        img_bytes = await photo_file.download_as_bytearray()
        
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")
        
        user_caption = update.message.caption.strip() if update.message.caption else None
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}"
        
        prompt_text = (
            "Anda adalah ahli gizi bersertifikat. Tugas Anda adalah menganalisis makanan pada gambar yang diberikan.\n"
            "1. Identifikasi semua makanan dan minuman yang terlihat.\n"
            "2. Perkirakan berat/porsi masing-masing secara visual. Jika pengguna memberikan informasi gramasi/keterangan tambahan, gunakan informasi tersebut sebagai acuan utama.\n"
            "3. Estimasi jumlah Kalori (kcal), Protein (g), Karbohidrat (g), dan Lemak (g) berdasarkan USDA atau TKPI (Tabel Komposisi Pangan Indonesia).\n"
            "4. Berikan total nutrisi.\n"
            "5. Berikan saran/tips singkat tentang gizi makanan tersebut (misal: tinggi protein, tinggi lemak jenuh, kurang serat, dll.).\n\n"
            "PENTING: Tuliskan respon Anda dalam BAHASA INDONESIA dan gunakan format HTML Telegram. "
            "Hanya gunakan tag HTML berikut: <b> untuk tebal, <i> untuk miring, <code> untuk teks kode, <pre> untuk blok kode. "
            "Jangan gunakan format markdown (seperti **, *, `) sama sekali, dan jangan gunakan tag HTML selain yang disebutkan. "
            "Di baris paling pertama/kedua, berikan rangkuman satu baris dalam format yang persis seperti ini:\n"
            "===LOG_SUMMARY===\n"
            "[Nama makanan utama] (~[total_kalori] kcal, [total_protein]g protein)\n"
            "===END_LOG_SUMMARY==="
        )
        
        if user_caption:
            prompt_text += f"\n\nInformasi tambahan dari pengguna mengenai porsi/berat/makanan: {user_caption}"
            
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt_text
                        },
                        {
                            "inlineData": {
                                "mimeType": "image/jpeg",
                                "data": img_base64
                            }
                        }
                    ]
                }
            ]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30.0)
            
        if response.status_code != 200:
            raise Exception(f"Gemini API returned status {response.status_code}: {response.text}")
            
        result = response.json()
        candidates = result.get("candidates", [])
        if not candidates:
            raise Exception("No analysis result returned from Gemini API.")
            
        content_text = candidates[0]["content"]["parts"][0]["text"]
        
        log_summary = "Porsi Makanan"
        summary_match = re.search(r"===LOG_SUMMARY===\s*(.*?)\s*===END_LOG_SUMMARY===", content_text, re.DOTALL)
        if summary_match:
            log_summary = summary_match.group(1).strip()
            content_text = content_text.replace(summary_match.group(0), "").strip()
            
        ctx.user_data["pending_food_log"] = {
            "text": log_summary,
            "date": date.today().isoformat(),
            "time": datetime.now().strftime("%H:%M:%S")
        }
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Simpan ke Jurnal", callback_data="save_food_log"),
                InlineKeyboardButton("❌ Batal", callback_data="cancel_food_log")
            ]
        ]
        
        try:
            await loading_msg.delete()
            remove_from_history(chat_id, loading_msg.message_id)
        except Exception:
            pass
            
        msg = await update.message.reply_html(
            f"🍳 <b>HASIL ANALISIS NUTRISI</b>\n\n{content_text}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        append_to_history(chat_id, msg.message_id)
        
    except Exception as e:
        try:
            await loading_msg.delete()
            remove_from_history(chat_id, loading_msg.message_id)
        except Exception:
            pass
        msg = await update.message.reply_html(f"❌ <b>Gagal menganalisis foto:</b> <code>{html.escape(str(e))}</code>")
        append_to_history(chat_id, msg.message_id)
