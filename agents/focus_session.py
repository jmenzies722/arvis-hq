#!/usr/bin/env python3
"""Focus Session tracker — log and summarize deep work blocks."""
import json, sys, urllib.request, urllib.parse
from pathlib import Path
from datetime import datetime

BASE     = Path.home() / "agent-hq"
LOG_FILE = BASE / "data" / "focus_log.json"
BOT      = "8696349618:AAFsqhznbNOWoRLXZ4ugzXOEzLmaRyi9geE"
CHAT     = "8743898908"

def load():
    try: return json.loads(LOG_FILE.read_text())
    except: return []

def save(data):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOG_FILE.write_text(json.dumps(data, indent=2))

def notify(msg):
    url  = f"https://api.telegram.org/bot{BOT}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": CHAT, "text": msg}).encode()
    try: urllib.request.urlopen(url, data, timeout=6)
    except: pass

def log_session(duration_min, goal):
    sessions = load()
    entry = {
        "id": len(sessions) + 1,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(),
        "duration_min": int(duration_min),
        "goal": goal,
    }
    sessions.append(entry)
    save(sessions)
    today_str = entry["date"]
    today     = [s for s in sessions if s["date"] == today_str]
    total_min = sum(s["duration_min"] for s in today)
    hours, mins = divmod(total_min, 60)
    time_str = f"{hours}h {mins}m" if hours else f"{mins}m"
    notify(
        f"Focus session logged — {duration_min}min\n"
        f"Goal: {goal}\n"
        f"Today total: {time_str} across {len(today)} session{'s' if len(today) != 1 else ''}"
    )
    print(f"Focus: {duration_min}min — {goal}")

def summary():
    sessions = load()
    today_str = datetime.now().strftime("%Y-%m-%d")
    today     = [s for s in sessions if s["date"] == today_str]
    total_min = sum(s["duration_min"] for s in today)
    week      = [s for s in sessions if s["date"] >= datetime.now().strftime("%Y-%m-")
                  and s["date"] <= today_str]
    week_min  = sum(s["duration_min"] for s in week)
    print(f"Today: {total_min}min | This month: {week_min}min | Total sessions: {len(sessions)}")
    return {"today_min": total_min, "sessions_today": len(today), "total": len(sessions)}

if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "summary":
        summary()
    elif len(args) >= 2:
        log_session(args[0], " ".join(args[1:]))
    else:
        print("Usage: focus_session.py <minutes> <goal>  OR  focus_session.py summary")
