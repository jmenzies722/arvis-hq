#!/usr/bin/env python3
"""Net Worth Tracker — manual balance entries, weekly trend, Telegram alerts."""
import json, sys, urllib.request, urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

BASE     = Path.home() / "agent-hq"
LOG_FILE = BASE / "data" / "net_worth.json"
BOT      = "8696349618:AAFsqhznbNOWoRLXZ4ugzXOEzLmaRyi9geE"
CHAT     = "8743898908"

ACCOUNTS = {
    "sofi":     {"name": "SoFi Emergency Fund", "type": "savings"},
    "roth":     {"name": "Roth IRA",            "type": "investment"},
    "fxaix":    {"name": "FXAIX",               "type": "investment"},
    "checking": {"name": "Checking",             "type": "cash"},
    "other":    {"name": "Other",                "type": "misc"},
}

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

def update(account, amount):
    entries = load()
    today = datetime.now().strftime("%Y-%m-%d")
    # Remove today's entry for this account if exists
    entries = [e for e in entries if not (e["date"] == today and e["account"] == account)]
    entries.append({
        "date": today,
        "timestamp": datetime.now().isoformat(),
        "account": account,
        "amount": float(amount),
    })
    save(entries)
    name = ACCOUNTS.get(account, {}).get("name", account)
    print(f"Updated {name}: ${float(amount):,.2f}")
    snapshot()

def snapshot():
    """Show current net worth across all accounts with weekly delta."""
    entries = load()
    today = datetime.now().strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    # Latest balance per account
    latest = {}
    for e in sorted(entries, key=lambda x: x["date"]):
        latest[e["account"]] = e["amount"]

    # 7 days ago balance per account
    old = {}
    for e in entries:
        if e["date"] <= week_ago:
            old[e["account"]] = e["amount"]

    total_now = sum(latest.values())
    total_old = sum(old.values()) if old else total_now
    delta = total_now - total_old
    delta_str = f"+${delta:,.0f}" if delta >= 0 else f"-${abs(delta):,.0f}"

    lines = [f"NET WORTH SNAPSHOT — {today}", ""]
    for key, info in ACCOUNTS.items():
        bal = latest.get(key, 0)
        if bal > 0:
            lines.append(f"{info['name']}: ${bal:,.2f}")

    lines.append("")
    lines.append(f"TOTAL: ${total_now:,.2f}")
    lines.append(f"7-day change: {delta_str}")

    # Milestones
    milestones = [5000, 10000, 15000, 20000, 25000, 30000, 50000, 75000, 100000]
    next_milestone = next((m for m in milestones if m > total_now), None)
    if next_milestone:
        to_go = next_milestone - total_now
        lines.append(f"Next milestone: ${next_milestone:,} (${to_go:,.0f} away)")

    msg = "\n".join(lines)
    print(msg)
    notify(msg)
    return total_now

def check_milestones():
    """Alert if a milestone was crossed since last check."""
    entries = load()
    if len(entries) < 2:
        return
    # Get last two distinct totals
    by_date = {}
    for e in entries:
        by_date.setdefault(e["date"], {})[e["account"]] = e["amount"]
    dates = sorted(by_date.keys())
    if len(dates) < 2:
        return
    prev_total = sum(by_date[dates[-2]].values())
    curr_total = sum(by_date[dates[-1]].values())
    milestones = [5000, 10000, 15000, 20000, 25000, 30000, 50000, 75000, 100000]
    for m in milestones:
        if prev_total < m <= curr_total:
            notify(f"MILESTONE HIT: ${m:,} net worth! Total: ${curr_total:,.2f}. Keep stacking.")
            print(f"Milestone crossed: ${m:,}")

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "snapshot":
        snapshot()
    elif args[0] == "update" and len(args) >= 3:
        update(args[1], args[2])
        check_milestones()
    else:
        print("Usage:")
        print("  net_worth_tracker.py snapshot")
        print("  net_worth_tracker.py update <account> <amount>")
        print(f"  Accounts: {', '.join(ACCOUNTS.keys())}")
