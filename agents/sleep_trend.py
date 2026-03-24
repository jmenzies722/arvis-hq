#!/usr/bin/env python3
"""Sleep Trend Analyzer — reads habit_log, sends 7-day sleep report to Telegram."""
import json, sys, urllib.request, urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

BASE      = Path.home() / "agent-hq"
HABIT_LOG = BASE / "data" / "habit_log.json"
BOT       = "8696349618:AAFsqhznbNOWoRLXZ4ugzXOEzLmaRyi9geE"
CHAT      = "8743898908"

def load_habits():
    try: return json.loads(HABIT_LOG.read_text())
    except: return []

def notify(msg):
    url  = f"https://api.telegram.org/bot{BOT}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": CHAT, "text": msg}).encode()
    try: urllib.request.urlopen(url, data, timeout=6)
    except: pass

def trend():
    entries  = load_habits()
    today    = datetime.now().date()
    week_ago = today - timedelta(days=7)
    recent   = [
        e for e in entries
        if e.get("sleep_hours") and e["date"] >= str(week_ago)
    ]
    recent = sorted(recent, key=lambda x: x["date"])

    if not recent:
        msg = "No sleep data logged yet. Start logging habits daily."
        print(msg)
        notify(msg)
        return

    hours = [float(e["sleep_hours"]) for e in recent]
    avg   = sum(hours) / len(hours)
    best  = max(hours)
    worst = min(hours)
    under_7 = sum(1 for h in hours if h < 7)

    # Grade
    if avg >= 8:
        grade = "A — Excellent"
        note  = "You're sleeping well. Keep it up."
    elif avg >= 7:
        grade = "B — Good"
        note  = "Solid. One more hour would level you up."
    elif avg >= 6:
        grade = "C — Below target"
        note  = f"{under_7} nights under 7h this week. Cognition and recovery are taking a hit."
    else:
        grade = "D — Sleep deprived"
        note  = "Serious deficit. Protect your sleep — it's compounding against you."

    # Bar per day
    lines = [f"SLEEP REPORT — {str(week_ago)} to {str(today)}\n"]
    for e in recent:
        h     = float(e["sleep_hours"])
        bar   = "#" * int(h) + "." * max(0, 8 - int(h))
        flag  = " <-- low" if h < 7 else ""
        lines.append(f"  {e['date']}: {bar} {h}h{flag}")

    lines.append("")
    lines.append(f"Average:  {avg:.1f}h")
    lines.append(f"Best:     {best}h")
    lines.append(f"Worst:    {worst}h")
    lines.append(f"Under 7h: {under_7} nights")
    lines.append(f"\nGrade: {grade}")
    lines.append(note)

    msg = "\n".join(lines)
    print(msg)
    notify(msg)

if __name__ == "__main__":
    trend()
