import json
import os
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore

SCHEDULE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reminders.json")
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(jobstores={"default": MemoryJobStore()})

job_map = {}


def _load_reminders():
    if not os.path.exists(SCHEDULE_FILE):
        return {"reminders": [], "next_id": 1}
    with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_reminders(data):
    with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


async def send_reminder(bot, chat_id, text):
    from telegram.helpers import escape_markdown
    msg = f"⏰ *Reminder*\n\n{escape_markdown(text, version=2)}"
    try:
        await bot.send_message(chat_id=chat_id, text=msg, parse_mode="MarkdownV2")
    except Exception as e:
        try:
            await bot.send_message(chat_id=chat_id, text=f"⏰ Reminder:\n\n{text}")
        except Exception:
            logger.error(f"Failed to send reminder: {e}")


def add_reminder(bot, chat_id: int, text: str, remind_at: datetime, repeat: str = None) -> dict:
    data = _load_reminders()
    rid = data["next_id"]
    entry = {
        "id": rid,
        "chat_id": chat_id,
        "text": text,
        "remind_at": remind_at.isoformat(),
        "repeat": repeat,
        "created_at": datetime.now().isoformat(),
        "active": True,
    }
    data["reminders"].append(entry)
    data["next_id"] += 1
    _save_reminders(data)

    job_id = f"reminder_{rid}"
    if repeat == "daily":
        trigger = CronTrigger(hour=remind_at.hour, minute=remind_at.minute)
    elif repeat == "weekly":
        trigger = CronTrigger(day_of_week=remind_at.weekday(), hour=remind_at.hour, minute=remind_at.minute)
    elif repeat:
        parts = repeat.lower().replace("every ", "").split()
        if len(parts) >= 2 and parts[1] in ("minute", "minutes", "hour", "hours"):
            val = int(parts[0])
            unit = parts[1]
            if "hour" in unit:
                trigger = IntervalTrigger(hours=val)
            else:
                trigger = IntervalTrigger(minutes=val)
        else:
            trigger = DateTrigger(run_date=remind_at)
    else:
        trigger = DateTrigger(run_date=remind_at)

    scheduler.add_job(
        send_reminder,
        trigger=trigger,
        args=[bot, chat_id, text],
        id=job_id,
        replace_existing=True,
    )
    job_map[rid] = job_id
    return entry


def remove_reminder(rid: int) -> bool:
    data = _load_reminders()
    for r in data["reminders"]:
        if r["id"] == rid:
            r["active"] = False
            _save_reminders(data)
            job_id = job_map.pop(rid, None)
            if job_id:
                scheduler.remove_job(job_id)
            return True
    return False


def get_reminders(chat_id: int = None) -> list:
    data = _load_reminders()
    reminders = [r for r in data["reminders"] if r["active"]]
    if chat_id:
        reminders = [r for r in reminders if r["chat_id"] == chat_id]
    return reminders


def restore_reminders(bot):
    data = _load_reminders()
    for r in data["reminders"]:
        if not r["active"]:
            continue
        rid = r["id"]
        remind_at = datetime.fromisoformat(r["remind_at"])
        now = datetime.now()
        if remind_at <= now and not r["repeat"]:
            continue
        repeat = r["repeat"]
        job_id = f"reminder_{rid}"
        if repeat == "daily":
            trigger = CronTrigger(hour=remind_at.hour, minute=remind_at.minute)
        elif repeat == "weekly":
            trigger = CronTrigger(day_of_week=remind_at.weekday(), hour=remind_at.hour, minute=remind_at.minute)
        elif repeat:
            parts = repeat.lower().replace("every ", "").split()
            if len(parts) >= 2 and parts[1] in ("minute", "minutes", "hour", "hours"):
                val = int(parts[0])
                unit = parts[1]
                if "hour" in unit:
                    trigger = IntervalTrigger(hours=val)
                else:
                    trigger = IntervalTrigger(minutes=val)
            else:
                continue
        else:
            if remind_at <= now:
                continue
            trigger = DateTrigger(run_date=remind_at)

        scheduler.add_job(
            send_reminder,
            trigger=trigger,
            args=[bot, r["chat_id"], r["text"]],
            id=job_id,
            replace_existing=True,
        )
        job_map[rid] = job_id
