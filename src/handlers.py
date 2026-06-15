from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, filters

from src.commands import (
    start, cmd_log, cmd_agenda, cmd_today, cmd_yesterday, cmd_date,
    cmd_search, cmd_all, cmd_stats, cmd_del, cmd_clear, cmd_restart,
    cmd_remind, cmd_remindat, cmd_reminders, cmd_unremind, cmd_rank,
    cmd_export, cmd_ai, auto_log
)
from src.callbacks import menu_callback
from src.helpers import _show_delete_list


def get_handlers():
    return [
        CommandHandler("start", start),
        CommandHandler("log", cmd_log),
        CommandHandler("agenda", cmd_agenda),
        CommandHandler("today", cmd_today),
        CommandHandler("yesterday", cmd_yesterday),
        CommandHandler("date", cmd_date),
        CommandHandler("search", cmd_search),
        CommandHandler("all", cmd_all),
        CommandHandler("stats", cmd_stats),
        CommandHandler("rank", cmd_rank),
        CommandHandler("export", cmd_export),
        CommandHandler("ai", cmd_ai),
        CommandHandler("del", cmd_del),
        CommandHandler("clear", cmd_clear),
        CommandHandler("restart", cmd_restart),
        CommandHandler("remind", cmd_remind),
        CommandHandler("remindat", cmd_remindat),
        CommandHandler("reminders", cmd_reminders),
        CommandHandler("unremind", cmd_unremind),
        CallbackQueryHandler(menu_callback, pattern="^(menu_|export_|add_remind_|set_daily_|set_once_|del_remind_|list_reminders|toggle_del_|delete_selected|delete_all_today)"),
        MessageHandler(filters.TEXT & ~filters.COMMAND, auto_log),
    ]
