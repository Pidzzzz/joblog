import json, os
from datetime import date, datetime

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "journal.json")

def _load():
    if not os.path.exists(DATA_FILE):
        return {"entries": [], "next_id": 1}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def add_entry(text: str, entry_date: str = None, entry_time: str = None) -> dict:
    data = _load()
    now = datetime.now()
    entry = {
        "id": data["next_id"],
        "date": entry_date or now.strftime("%Y-%m-%d"),
        "time": entry_time or now.strftime("%H:%M:%S"),
        "text": text.strip(),
        "created_at": now.isoformat()
    }
    data["entries"].append(entry)
    data["next_id"] += 1
    _save(data)
    return entry

def get_by_date(date_str: str) -> list:
    data = _load()
    return [e for e in data["entries"] if e["date"] == date_str]

def get_today() -> list:
    return get_by_date(date.today().isoformat())

def get_yesterday() -> list:
    from datetime import timedelta
    d = (date.today() - timedelta(days=1)).isoformat()
    return get_by_date(d)

def search(keyword: str) -> list:
    data = _load()
    kw = keyword.lower()
    return [e for e in data["entries"] if kw in e["text"].lower()]

def get_all_dates() -> list:
    data = _load()
    dates = {}
    for e in data["entries"]:
        dates[e["date"]] = dates.get(e["date"], 0) + 1
    return sorted(dates.items(), reverse=True)

def get_stats() -> dict:
    data = _load()
    entries = data["entries"]
    if not entries:
        return {"total": 0, "days": 0, "first_date": None, "last_date": None}
    dates = sorted(set(e["date"] for e in entries))
    return {
        "total": len(entries),
        "days": len(dates),
        "first_date": dates[0],
        "last_date": dates[-1]
    }

def get_entry_count() -> int:
    return _load()["next_id"] - 1

def delete_entry(entry_id: int) -> bool:
    data = _load()
    for i, e in enumerate(data["entries"]):
        if e["id"] == entry_id:
            data["entries"].pop(i)
            _save(data)
            return True
    return False
