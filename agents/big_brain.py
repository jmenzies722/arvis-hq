#!/usr/bin/env python3
"""
Big Brain — Meta-Orchestration Agent
Knows Josh's goals, coordinates all agents, surfaces priorities and blockers.
The central intelligence layer of Arvis OS.

Goals it tracks:
- Career: Platform Eng → AI Solutions Eng → Technical Co-Founder
- Financial: $7K SoFi → Roth IRA → FXAIX → FI by mid-30s
- Health: Daily push-ups, sleep, habits
- Work: Kiro rollout, Claude Enterprise, Compliance API
"""
import json, sys, subprocess
from datetime import datetime
from pathlib import Path

BASE     = Path(__file__).parent.parent
DATA_DIR = BASE / "data"

def get_today_snapshot():
    today = datetime.now().strftime("%Y-%m-%d")
    snapshot = {}

    # Pushups
    try:
        from collections import defaultdict
        logs = json.loads((Path.home() / "workout-agent" / "logs.json").read_text())
        daily = defaultdict(int)
        for l in logs:
            daily[l["date"]] += l.get("total_reps", 0)
        snapshot["pushups_today"] = daily.get(today, 0)
    except Exception:
        snapshot["pushups_today"] = 0

    # Savings
    try:
        nw = json.loads((DATA_DIR / "net_worth.json").read_text())
        by_acct = {e.get("account",""): e.get("amount",0) for e in nw}
        snapshot["sofi"] = by_acct.get("sofi", 0)
        snapshot["roth"] = by_acct.get("roth", 0)
        snapshot["fxaix"] = by_acct.get("fxaix", 0)
    except Exception:
        pass

    # Habit
    try:
        habit_log = json.loads((DATA_DIR / "habit_log.json").read_text())
        today_habit = next((h for h in habit_log if h.get("date") == today), None)
        snapshot["habit_logged"] = today_habit is not None
        snapshot["sleep"] = today_habit.get("sleep_hours") if today_habit else None
    except Exception:
        snapshot["habit_logged"] = False

    # Activity runs today
    try:
        activity = json.loads((DATA_DIR / "activity_log.json").read_text())
        snapshot["agent_runs_today"] = len([a for a in activity if a.get("date") == today])
    except Exception:
        snapshot["agent_runs_today"] = 0

    return snapshot

def priorities():
    snap = get_today_snapshot()
    lines = [f"Big Brain — {datetime.now().strftime('%A, %b %-d %I:%M %p')}",
             "─" * 36, ""]

    # Urgent items (based on data)
    urgent = []
    if snap.get("pushups_today", 0) < 100:
        rem = 100 - snap.get("pushups_today", 0)
        urgent.append(f"Push-ups: {rem} reps to hit daily goal")
    if not snap.get("habit_logged"):
        urgent.append("Habit check-in: not logged today")
    if snap.get("sofi", 0) < 7000:
        gap = 7000 - snap.get("sofi", 0)
        urgent.append(f"SoFi: ${gap:,.0f} to emergency fund goal")

    if urgent:
        lines.append("⚠️  Today's Gaps")
        for u in urgent:
            lines.append(f"  • {u}")
        lines.append("")

    # Strategic priorities
    lines.append("🎯 Strategic Focus")
    lines.append("  1. Kiro rollout — document outcomes for Seth/Mike visibility")
    lines.append("  2. Claude Enterprise — Compliance API architecture")
    lines.append("  3. AWS SAA Pro — 1 lesson/day via Daily Learning agent")
    lines.append("  4. Net worth — update Roth + FXAIX balances")
    lines.append("")

    # Today's agent activity
    lines.append(f"⚡ {snap.get('agent_runs_today', 0)} agent runs today")
    lines.append("")
    lines.append("— Arvis Big Brain")

    output = "\n".join(lines)
    print(output)
    return output

def run():
    priorities()

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "run":
        run()
    elif cmd == "priorities":
        priorities()
