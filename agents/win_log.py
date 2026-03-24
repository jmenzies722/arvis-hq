#!/usr/bin/env python3
"""Win Log — capture work wins at Nectar for career leverage and LinkedIn content."""
import json, sys, urllib.request, urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

BASE     = Path.home() / "agent-hq"
LOG_FILE = BASE / "data" / "wins.json"
BOT      = "8696349618:AAFsqhznbNOWoRLXZ4ugzXOEzLmaRyi9geE"
CHAT     = "8743898908"

CATEGORIES = ["kiro", "claude", "infra", "leadership", "learning", "personal", "income"]

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

def log_win(category, description, impact=""):
    entries = load()
    today = datetime.now().strftime("%Y-%m-%d")
    entry = {
        "id": len(entries) + 1,
        "date": today,
        "timestamp": datetime.now().isoformat(),
        "category": category.lower(),
        "description": description,
        "impact": impact,
    }
    entries.append(entry)
    save(entries)
    cat_label = category.upper()
    msg = f"Win logged [{cat_label}]\n{description}"
    if impact:
        msg += f"\nImpact: {impact}"
    print(msg)
    notify(msg)

def weekly_digest():
    entries = load()
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    recent = [e for e in entries if e["date"] >= week_ago]
    if not recent:
        notify("No wins logged this week. Change that.")
        print("No wins this week.")
        return
    by_cat = {}
    for e in recent:
        cat = e["category"]
        by_cat.setdefault(cat, []).append(e)
    lines = [f"WIN DIGEST — Last 7 Days ({len(recent)} wins)\n"]
    for cat, wins in sorted(by_cat.items()):
        lines.append(f"[{cat.upper()}]")
        for w in wins:
            lines.append(f"  {w['date']}: {w['description']}")
            if w.get("impact"):
                lines.append(f"    Impact: {w['impact']}")
    lines.append(f"\nTotal logged: {len(entries)} all-time wins")
    msg = "\n".join(lines)
    print(msg)
    notify(msg)

def summary():
    entries = load()
    if not entries:
        print("No wins logged yet.")
        return
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_wins = [e for e in entries if e["date"] == today_str]
    print(f"Today: {len(today_wins)} wins | All-time: {len(entries)}")
    for w in today_wins:
        print(f"  [{w['category'].upper()}] {w['description']}")

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "summary":
        summary()
    elif args[0] == "digest":
        weekly_digest()
    elif args[0] == "log" and len(args) >= 3:
        category    = args[1]
        description = " ".join(args[2:])
        log_win(category, description)
    else:
        print("Usage:")
        print("  win_log.py log <category> <description>")
        print("  win_log.py digest")
        print("  win_log.py summary")
        print(f"  Categories: {', '.join(CATEGORIES)}")
