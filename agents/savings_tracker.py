#!/usr/bin/env python3
"""
Savings Goal Tracker
Track progress toward financial goals
Usage: python3 savings_tracker.py update sofi 3500
       python3 savings_tracker.py status
"""
import json, sys, urllib.request, urllib.parse
from datetime import datetime
from pathlib import Path

DATA_FILE = Path.home() / "agent-hq" / "data" / "savings.json"
BOT_TOKEN = "8696349618:AAFsqhznbNOWoRLXZ4ugzXOEzLmaRyi9geE"
CHAT_ID = "8743898908"

GOALS = {
    "sofi":    {"name": "SoFi Emergency Fund", "target": 7000,  "emoji": "🏦"},
    "roth":    {"name": "Roth IRA",            "target": 7000,  "emoji": "📈"},
    "fxaix":   {"name": "FXAIX Investments",   "target": 50000, "emoji": "💹"},
}

def load():
    if not DATA_FILE.exists():
        return {k: {"balance": 0, "history": []} for k in GOALS}
    return json.loads(DATA_FILE.read_text())

def save(data):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, indent=2))

def notify(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": msg}).encode()
    urllib.request.urlopen(url, data)

def update(account, amount):
    data = load()
    if account not in data:
        data[account] = {"balance": 0, "history": []}
    data[account]["balance"] = float(amount)
    data[account]["history"].append({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "balance": float(amount)
    })
    save(data)
    print(f"✅ Updated {account}: ${amount}")

def status():
    data = load()
    lines = ["💰 SAVINGS STATUS\n"]
    total_saved = 0
    for key, goal in GOALS.items():
        balance = data.get(key, {}).get("balance", 0)
        target = goal["target"]
        pct = min(int((balance / target) * 100), 100)
        bar_filled = int(pct / 10)
        bar = "█" * bar_filled + "░" * (10 - bar_filled)
        remaining = max(target - balance, 0)
        total_saved += balance
        lines.append(f"{goal['emoji']} {goal['name']}")
        lines.append(f"${balance:,.0f} / ${target:,} ({pct}%)")
        lines.append(f"[{bar}]")
        if remaining > 0:
            lines.append(f"${remaining:,.0f} to go\n")
        else:
            lines.append("✅ GOAL MET!\n")

    lines.append(f"Total saved: ${total_saved:,.0f}")
    msg = "\n".join(lines)
    print(msg)
    notify(msg)

MILESTONES = {
    "sofi":  [1000, 2000, 3500, 5000, 7000],
    "roth":  [1000, 2500, 5000, 7000],
    "fxaix": [1000, 5000, 10000, 25000, 50000],
}

def check_milestones(account, new_amount):
    data = load()
    history = data.get(account, {}).get("history", [])
    prev_amount = history[-2]["balance"] if len(history) >= 2 else 0
    for m in MILESTONES.get(account, []):
        if prev_amount < m <= float(new_amount):
            goal_name = GOALS.get(account, {}).get("name", account)
            notify(f"MILESTONE: ${m:,} reached in {goal_name}! Balance: ${float(new_amount):,.2f}")
            print(f"Milestone hit: ${m:,} in {account}")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "update":
        acct = sys.argv[2] if len(sys.argv) > 2 else ""
        amt  = sys.argv[3] if len(sys.argv) > 3 else "0"
        update(acct, amt)
        check_milestones(acct, amt)
    elif cmd == "status":
        status()
