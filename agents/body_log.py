#!/usr/bin/env python3
"""Body metrics log — weight, mood, energy."""
import json, sys, urllib.request, urllib.parse
from pathlib import Path
from datetime import datetime

BASE     = Path.home() / "agent-hq"
LOG_FILE = BASE / "data" / "body_log.json"
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

def log_body(weight_lbs, mood, energy):
    entries = load()
    today   = datetime.now().strftime("%Y-%m-%d")
    entry = {
        "date": today,
        "timestamp": datetime.now().isoformat(),
        "weight_lbs": float(weight_lbs),
        "mood": int(mood),       # 1-5
        "energy": int(energy),   # 1-5
    }
    entries = [e for e in entries if e["date"] != today]
    entries.append(entry)
    save(entries)
    # 7-day weight trend
    recent = sorted([e for e in entries if "weight_lbs" in e], key=lambda x: x["date"])[-7:]
    if len(recent) >= 2:
        delta  = float(weight_lbs) - recent[0]["weight_lbs"]
        trend  = f"  ({'+' if delta >= 0 else ''}{delta:.1f} lbs this week)"
    else:
        trend  = ""
    mood_bars   = "+" * int(mood) + "-" * (5 - int(mood))
    energy_bars = "+" * int(energy) + "-" * (5 - int(energy))
    notify(
        f"Body check-in — {today}\n"
        f"Weight: {weight_lbs} lbs{trend}\n"
        f"Mood:   [{mood_bars}] {mood}/5\n"
        f"Energy: [{energy_bars}] {energy}/5"
    )
    print(f"Body log: {weight_lbs}lbs mood={mood}/5 energy={energy}/5")

def summary():
    entries = load()
    if not entries:
        print("No body logs yet")
        return {}
    latest = sorted(entries, key=lambda x: x["date"])[-1]
    print(f"Latest ({latest['date']}): {latest.get('weight_lbs','-')}lbs mood={latest.get('mood','-')}/5 energy={latest.get('energy','-')}/5")
    return latest

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "summary":
        summary()
    elif len(args) >= 3:
        log_body(*args[:3])
    else:
        print("Usage: body_log.py <weight_lbs> <mood 1-5> <energy 1-5>")
