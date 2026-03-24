#!/usr/bin/env python3
"""
Weekly Recap Agent — runs every Sunday
Summarizes the week: workouts, learning, budget, savings
"""
import json, urllib.request, urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

BOT_TOKEN = "8696349618:AAFsqhznbNOWoRLXZ4ugzXOEzLmaRyi9geE"
CHAT_ID   = "8743898908"

WORKOUT_LOG = Path.home() / "workout-agent" / "logs.json"
BUDGET_LOG  = Path.home() / "agent-hq" / "data" / "budget.json"
SAVINGS_LOG = Path.home() / "agent-hq" / "data" / "savings.json"

def notify(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": msg}).encode()
    urllib.request.urlopen(url, data)

def week_dates():
    today = datetime.now().date()
    start = today - timedelta(days=7)
    return [str(start + timedelta(days=i)) for i in range(8)]

def workout_summary(dates):
    if not WORKOUT_LOG.exists(): return "No data"
    logs = json.loads(WORKOUT_LOG.read_text())
    week_logs = [l for l in logs if l["date"] in dates]
    total = sum(l["total_reps"] for l in week_logs)
    days = len(set(l["date"] for l in week_logs))
    return f"{total} push-ups across {days} days"

def budget_summary(dates):
    if not BUDGET_LOG.exists(): return "No data"
    expenses = json.loads(BUDGET_LOG.read_text())
    week_exp = [e for e in expenses if e["date"] in dates]
    total = sum(e["amount"] for e in week_exp)
    by_cat = defaultdict(float)
    for e in week_exp: by_cat[e["category"]] += e["amount"]
    top = sorted(by_cat.items(), key=lambda x: -x[1])[:3]
    top_str = ", ".join(f"{c}: ${v:.0f}" for c, v in top) if top else "none"
    return f"${total:.0f} spent. Top: {top_str}"

def savings_snapshot():
    if not SAVINGS_LOG.exists(): return "No data"
    data = json.loads(SAVINGS_LOG.read_text())
    sofi = data.get("sofi", {}).get("balance", 0)
    roth = data.get("roth", {}).get("balance", 0)
    return f"SoFi: ${sofi:,.0f} / $7K | Roth: ${roth:,.0f} / $7K"

def run():
    dates = week_dates()
    week_start = (datetime.now() - timedelta(days=7)).strftime("%b %d")
    week_end   = datetime.now().strftime("%b %d")

    lines = [
        f"📊 WEEKLY RECAP — {week_start} → {week_end}\n",
        f"💪 Fitness\n  {workout_summary(dates)}\n",
        f"💸 Spending\n  {budget_summary(dates)}\n",
        f"🏦 Savings\n  {savings_snapshot()}\n",
        "Keep building. 🚀",
    ]
    msg = "\n".join(lines)
    print(msg)
    notify(msg)

if __name__ == "__main__":
    run()
