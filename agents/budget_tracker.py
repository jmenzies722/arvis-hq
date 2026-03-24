#!/usr/bin/env python3
"""
Budget Tracker Agent
Log expenses via: python3 budget_tracker.py log 50 groceries
View summary via: python3 budget_tracker.py summary
"""
import json, sys, os
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

DATA_FILE = Path.home() / "agent-hq" / "data" / "budget.json"
BOT_TOKEN = "8696349618:AAFsqhznbNOWoRLXZ4ugzXOEzLmaRyi9geE"
CHAT_ID = "8743898908"

MONTHLY_BUDGET = {
    "food": 400, "transport": 150, "entertainment": 100,
    "shopping": 200, "health": 100, "other": 200
}

CATEGORY_KEYWORDS = {
    "food": ["grocery","groceries","food","lunch","dinner","breakfast","restaurant","coffee","eat","chipotle","mcdonalds","pizza"],
    "transport": ["gas","uber","lyft","train","bus","parking","toll","car","lirr"],
    "entertainment": ["movie","netflix","spotify","game","bar","concert","ticket","date"],
    "shopping": ["amazon","target","walmart","clothes","shirt","shoes","mall"],
    "health": ["gym","doctor","pharmacy","medicine","cvs","walgreens","supplement"],
}

def guess_category(note):
    note_lower = note.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(k in note_lower for k in keywords):
            return cat
    return "other"

def load():
    if not DATA_FILE.exists(): return []
    return json.loads(DATA_FILE.read_text())

def save(data):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, indent=2))

def notify(msg):
    import urllib.request, urllib.parse
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": msg}).encode()
    urllib.request.urlopen(url, data)

def log_expense(amount, note, category=None):
    expenses = load()
    if not category:
        category = guess_category(note)
    entry = {
        "id": len(expenses) + 1,
        "amount": float(amount),
        "note": note,
        "category": category,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M"),
        "month": datetime.now().strftime("%Y-%m"),
    }
    expenses.append(entry)
    save(expenses)
    print(f"✅ Logged: ${amount} — {note} ({category})")
    notify(f"💸 Expense logged!\n${amount} — {note}\nCategory: {category.title()}")
    return entry

def summary(month=None):
    expenses = load()
    if not month:
        month = datetime.now().strftime("%Y-%m")
    month_exp = [e for e in expenses if e.get("month") == month]
    by_cat = defaultdict(float)
    for e in month_exp:
        by_cat[e["category"]] += e["amount"]
    total = sum(by_cat.values())
    lines = [f"💰 BUDGET SUMMARY — {month}\n"]
    for cat, budget in MONTHLY_BUDGET.items():
        spent = by_cat.get(cat, 0)
        pct = int((spent / budget) * 100) if budget > 0 else 0
        bar = "█" * min(int(pct / 10), 10) + "░" * (10 - min(int(pct / 10), 10))
        flag = " ⚠️" if pct > 90 else ""
        lines.append(f"{cat.title()}: ${spent:.0f} / ${budget}{flag}")
    lines.append(f"\nTotal spent: ${total:.0f}")
    msg = "\n".join(lines)
    print(msg)
    notify(msg)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "summary"
    if cmd == "log":
        amount = sys.argv[2] if len(sys.argv) > 2 else "0"
        note = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else "unknown"
        log_expense(amount, note)
    elif cmd == "summary":
        summary()
