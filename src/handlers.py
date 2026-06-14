import os
from datetime import date
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

from src import storage

OWNER_ID = int(os.getenv("DEVELOPER_ID", "0"))

def _is_owner(update: Update) -> bool:
    return update.effective_user.id == OWNER_ID

def _fmt_entry(e: dict) -> str:
    return f"  #{e['id']}  [{e['time']}]  {e['text']}"

def _fmt_entries(entries: list, title: str = None) -> str:
    if not entries:
        return f"<b>{title}</b>\n\nTidak ada catatan." if title else "Tidak ada catatan."
    lines = [f"<b>{title}</b>\n"] if title else []
    for e in entries:
        lines.append(_fmt_entry(e))
    return "\n".join(lines)

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update):
        await update.message.reply_text("Bot ini pribadi.")
        return
    text = (
        "<b>SoloLeveling Journal</b>\n\n"
        "Catat semua aktivitas kerja mu disini.\n\n"
        "<b>Commands:</b>\n"
        "/log &lt;text&gt;  — Catat kegiatan\n"
        "/today  — Lihat catatan hari ini\n"
        "/yesterday  — Lihat catatan kemarin\n"
        "/date YYYY-MM-DD  — Lihat catatan tanggal tertentu\n"
        "/search &lt;kata&gt;  — Cari catatan\n"
        "/all  — Semua tanggal\n"
        "/stats  — Statistik\n"
        "/del &lt;id&gt;  — Hapus catatan\n\n"
        "<i>Atau kirim pesan langsung, otomatis tersimpan.</i>"
    )
    await update.message.reply_text(text, parse_mode="HTML")

async def cmd_log(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update):
        return
    text = " ".join(ctx.args)
    if not text:
        await update.message.reply_text("Gunakan: /log <teks kegiatan>")
        return
    entry = storage.add_entry(text)
    await update.message.reply_text(
        f"Disimpan:\n{_fmt_entry(entry)}",
        parse_mode="HTML"
    )

async def cmd_today(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update):
        return
    entries = storage.get_today()
    today_str = date.today().isoformat()
    msg = _fmt_entries(entries, f"Catatan Hari Ini ({today_str})")
    await update.message.reply_text(msg, parse_mode="HTML")

async def cmd_yesterday(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update):
        return
    entries = storage.get_yesterday()
    from datetime import timedelta
    yesterday_str = (date.today() - timedelta(days=1)).isoformat()
    msg = _fmt_entries(entries, f"Kemarin ({yesterday_str})")
    await update.message.reply_text(msg, parse_mode="HTML")

async def cmd_date(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update):
        return
    d = " ".join(ctx.args)
    if not d:
        await update.message.reply_text("Gunakan: /date YYYY-MM-DD")
        return
    entries = storage.get_by_date(d)
    msg = _fmt_entries(entries, f"Catatan ({d})")
    await update.message.reply_text(msg, parse_mode="HTML")

async def cmd_search(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update):
        return
    kw = " ".join(ctx.args)
    if not kw:
        await update.message.reply_text("Gunakan: /search <kata kunci>")
        return
    results = storage.search(kw)
    if not results:
        await update.message.reply_text(f"Tidak ditemukan catatan dengan kata: {kw}")
        return
    msg = _fmt_entries(results, f"Hasil pencarian: {kw} ({len(results)})")
    if len(msg) > 4000:
        msg = msg[:4000] + "\n\n... (terlalu panjang)"
    await update.message.reply_text(msg, parse_mode="HTML")

async def cmd_all(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update):
        return
    dates = storage.get_all_dates()
    if not dates:
        await update.message.reply_text("Belum ada catatan.")
        return
    total = storage.get_entry_count()
    lines = [f"<b>Semua Tanggal ({total} catatan)</b>\n"]
    for d, count in dates:
        lines.append(f"  {d}  ({count})")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update):
        return
    s = storage.get_stats()
    if s["total"] == 0:
        await update.message.reply_text("Belum ada catatan.")
        return
    text = (
        f"<b>Statistik Journal</b>\n\n"
        f"Total catatan: {s['total']}\n"
        f"Total hari: {s['days']}\n"
        f"Pertama: {s['first_date']}\n"
        f"Terakhir: {s['last_date']}"
    )
    await update.message.reply_text(text, parse_mode="HTML")

async def cmd_del(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update):
        return
    try:
        eid = int(" ".join(ctx.args))
    except (ValueError, IndexError):
        await update.message.reply_text("Gunakan: /del <id catatan>")
        return
    if storage.delete_entry(eid):
        await update.message.reply_text(f"Catatan #{eid} dihapus.")
    else:
        await update.message.reply_text(f"Catatan #{eid} tidak ditemukan.")

async def auto_log(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_owner(update):
        return
    text = update.message.text.strip()
    if not text:
        return
    entry = storage.add_entry(text)
    await update.message.reply_text(
        f"Disimpan:\n{_fmt_entry(entry)}",
        parse_mode="HTML"
    )

def get_handlers():
    return [
        CommandHandler("start", start),
        CommandHandler("log", cmd_log),
        CommandHandler("today", cmd_today),
        CommandHandler("yesterday", cmd_yesterday),
        CommandHandler("date", cmd_date),
        CommandHandler("search", cmd_search),
        CommandHandler("all", cmd_all),
        CommandHandler("stats", cmd_stats),
        CommandHandler("del", cmd_del),
        MessageHandler(filters.TEXT & ~filters.COMMAND, auto_log),
    ]
