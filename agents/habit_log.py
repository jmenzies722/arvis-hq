#!/usr/bin/env python3
"""Daily habit tracker — sleep, water, gym, reading, no phone before 8am."""
import json, sys, urllib.request, urllib.parse
from pathlib import Path
from datetime import datetime

BASE     = Path.home() / "agent-hq"
LOG_FILE = BASE / "data" / "habit_log.json"
BOT      = "8696349618:AAFsqhznbNOWoRLXZ4ugzXOEzLmaRyi9geE"
CHAT     = "8743898908"

HABITS = ["sleep_hours", "water_glasses", "gym", "reading_min", "no_phone_am"]

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

def log_habits(sleep, water, gym, reading, no_phone):
    entries = load()
    today   = datetime.now().strftime("%Y-%m-%d")
    entry = {
        "date": today,
        "timestamp": datetime.now().isoformat(),
        "sleep_hours": float(sleep),
        "water_glasses": int(water),
        "gym": gym.lower() in ("1", "yes", "true", "y"),
        "reading_min": int(reading),
        "no_phone_am": no_phone.lower() in ("1", "yes", "true", "y"),
    }
    # Replace today's entry if exists
    entries = [e for e in entries if e["date"] != today]
    entries.append(entry)
    save(entries)
    gym_str     = "Done" if entry["gym"] else "Skipped"
    phone_str   = "Clean" if entry["no_phone_am"] else "Checked"
    notify(
        f"Habit check-in — {today}\n"
        f"Sleep: {sleep}h  |  Water: {water} glasses\n"
        f"Gym: {gym_str}  |  Reading: {reading}min\n"
        f"Phone-free AM: {phone_str}"
    )
    print(f"Habits logged for {today}")

def streak(habit_key):
    entries = sorted(load(), key=lambda x: x["date"], reverse=True)
    count   = 0
    for e in entries:
        val = e.get(habit_key)
        if habit_key in ("gym", "no_phone_am") and val:
            count += 1
        elif habit_key == "sleep_hours" and val and float(val) >= 7:
            count += 1
        elif habit_key == "water_glasses" and val and int(val) >= 8:
            count += 1
        elif habit_key == "reading_min" and val and int(val) >= 10:
            count += 1
        else:
            break
    return count

def summary():
    entries   = load()
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_e   = next((e for e in entries if e["date"] == today_str), None)
    if today_e:
        print(f"Today: sleep={today_e['sleep_hours']}h water={today_e['water_glasses']} gym={'yes' if today_e['gym'] else 'no'} reading={today_e['reading_min']}min")
    else:
        print("No habit entry today yet")
    return today_e or {}

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "summary":
        summary()
    elif len(args) >= 5:
        log_habits(*args[:5])
    else:
        print("Usage: habit_log.py <sleep_h> <water_glasses> <gym y/n> <reading_min> <no_phone_am y/n>")
