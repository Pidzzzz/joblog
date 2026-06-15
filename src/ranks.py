from datetime import date, timedelta

RANKS = [
    {"rank": "E", "min_entries": 0, "title": "E-Rank Hunter", "emoji": "⬜"},
    {"rank": "D", "min_entries": 10, "title": "D-Rank Hunter", "emoji": "🟫"},
    {"rank": "C", "min_entries": 30, "title": "C-Rank Hunter", "emoji": "🟩"},
    {"rank": "B", "min_entries": 75, "title": "B-Rank Hunter", "emoji": "🟦"},
    {"rank": "A", "min_entries": 150, "title": "A-Rank Hunter", "emoji": "🟪"},
    {"rank": "S", "min_entries": 300, "title": "S-Rank Hunter", "emoji": "🟥"},
    {"rank": "National", "min_entries": 500, "title": "National Level Hunter", "emoji": "⬛"},
]

STREAK_MILESTONES = [
    (7, "Shadow Soldier", "⬜"),
    (14, "Riser", "🟫"),
    (30, "Commander", "🟩"),
    (60, "Marshal", "🟦"),
    (90, "Shadow Monarch", "🟥"),
]


def get_rank(total_entries: int) -> dict:
    current = RANKS[0]
    for r in RANKS:
        if total_entries >= r["min_entries"]:
            current = r
        else:
            break
    return current


def get_next_rank(total_entries: int) -> dict | None:
    for r in RANKS:
        if total_entries < r["min_entries"]:
            return r
    return None


def get_xp_progress(total_entries: int) -> dict:
    current = get_rank(total_entries)
    nxt = get_next_rank(total_entries)
    if nxt is None:
        return {
            "rank": current,
            "next": None,
            "entries_in_rank": total_entries - current["min_entries"],
            "entries_needed": 0,
            "percent": 100,
        }
    span = nxt["min_entries"] - current["min_entries"]
    progress = total_entries - current["min_entries"]
    percent = min(int(progress / span * 100), 100)
    return {
        "rank": current,
        "next": nxt,
        "entries_in_rank": progress,
        "entries_needed": span - progress,
        "percent": percent,
    }


def get_streak_info(entries: list) -> dict:
    if not entries:
        return {"streak": 0, "milestone": None}

    dates = sorted(set(e["date"] for e in entries), reverse=True)

    streak = 0
    check_date = date.today()

    for d in dates:
        if d == check_date.isoformat():
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break

    milestone = None
    for days, title, emoji in STREAK_MILESTONES:
        if streak >= days:
            milestone = {"days": days, "title": title, "emoji": emoji}

    return {"streak": streak, "milestone": milestone}


def format_progress_bar(percent: int, length: int = 10) -> str:
    filled = int(length * percent / 100)
    bar = "█" * filled + "░" * (length - filled)
    return bar
