#!/usr/bin/env python3
"""
Night Prep — pulls tomorrow's calendar + today's summary, sends to Telegram at 10:30pm.
"""
import subprocess, json, sys, urllib.request, urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

BOT_TOKEN = "8696349618:AAFsqhznbNOWoRLXZ4ugzXOEzLmaRyi9geE"
CHAT_ID   = "8743898908"
BASE      = Path(__file__).parent.parent

def tg(text):
    url  = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": text}).encode()
    urllib.request.urlopen(urllib.request.Request(url, data), timeout=10)

def applescript(script):
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=10)
    return r.stdout.strip()

def broadcast_to_hq(message, msg_type="outgoing"):
    try:
        url  = "http://localhost:8766/api/log/telegram"
        data = json.dumps({"message": message[:300], "type": msg_type}).encode()
        req  = urllib.request.Request(url, data, {"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=3)
    except Exception:
        pass

def get_tomorrow_calendar():
    script = '''
tell application "Calendar"
  set tomorrow to (current date) + 86400
  set tStart to tomorrow
  set hours of tStart to 0
  set minutes of tStart to 0
  set seconds of tStart to 0
  set tEnd to tStart + 86399
  set output to ""
  repeat with c in calendars
    try
      repeat with e in (events of c whose start date >= tStart and start date <= tEnd)
        set t to start date of e
        set h to hours of t
        set m to minutes of t
        set ampm to "AM"
        if h >= 12 then set ampm to "PM"
        if h > 12 then set h to h - 12
        if h = 0 then set h to 12
        set minStr to text -2 thru -1 of ("0" & m)
        set output to output & h & ":" & minStr & " " & ampm & " — " & summary of e & "\n"
      end repeat
    end try
  end repeat
  return output
end tell'''
    return applescript(script)

def get_today_stats():
    today = datetime.now().strftime("%Y-%m-%d")
    stats = {}
    try:
        log = BASE / "data" / "activity_log.json"
        if log.exists():
            runs   = json.loads(log.read_text())
            today_runs = [r for r in runs if r.get("date") == today and r.get("status") == "success"]
            stats["agent_runs"] = len(today_runs)
    except: pass
    try:
        wlog = BASE / "data" / "workout_log.json"
        if wlog.exists():
            d = json.loads(wlog.read_text())
            entries = [e for e in d.get("entries", []) if e.get("date") == today]
            stats["pushups"] = sum(e.get("reps", 0) for e in entries)
            stats["streak"]  = d.get("streak", 0)
    except: pass
    try:
        flog = BASE / "data" / "focus_log.json"
        if flog.exists():
            d = json.loads(flog.read_text())
            entries = [e for e in d.get("sessions", []) if e.get("date") == today]
            stats["focus_min"] = sum(e.get("duration_min", 0) for e in entries)
    except: pass
    try:
        elog = BASE / "data" / "expense_log.json"
        if elog.exists():
            d = json.loads(elog.read_text())
            entries = [e for e in d.get("expenses", []) if e.get("date") == today]
            stats["spent"] = sum(e.get("amount", 0) for e in entries)
    except: pass
    return stats

def main():
    tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%A, %b %-d")
    today_str    = datetime.now().strftime("%A, %b %-d")
    lines = [f"🌙 Night Prep — {today_str}\n{'─'*28}"]

    # Today's summary
    stats = get_today_stats()
    lines.append("\n📊 Today's Summary")
    if stats.get("pushups"):
        lines.append(f"  💪 Push-ups: {stats['pushups']} reps")
    if stats.get("focus_min"):
        lines.append(f"  🎯 Focus: {stats['focus_min']}min deep work")
    if stats.get("spent"):
        lines.append(f"  💸 Spent: ${stats['spent']:.2f}")
    if stats.get("agent_runs"):
        lines.append(f"  ⚡ Agent runs: {stats['agent_runs']}")
    if not any(stats.values()):
        lines.append("  Nothing logged today — remember to track tomorrow.")

    # Tomorrow's calendar
    cal = get_tomorrow_calendar()
    if cal.strip():
        lines.append(f"\n📅 Tomorrow — {tomorrow_str}")
        for ln in cal.strip().splitlines():
            if ln.strip():
                lines.append(f"  {ln.strip()}")
    else:
        lines.append(f"\n📅 Tomorrow — {tomorrow_str}")
        lines.append("  Nothing scheduled — good day to focus.")

    # Nightly reminders
    lines.append("\n✅ Before You Sleep")
    lines.append("  • Log any wins from today (win command)")
    lines.append("  • Did you hit your push-up goal?")
    lines.append("  • Set tomorrow's #1 priority now")

    lines.append("\n— Arvis. Sleep well.")
    msg = "\n".join(lines)
    tg(msg)
    print(msg)
    broadcast_to_hq(f"Night Prep sent — {today_str}", "outgoing")
    _log_run("night_prep", "Night Prep", "success", f"Night prep sent for {today_str}")

def _log_run(agent_id, agent_name, status, summary):
    try:
        log_file = BASE / "data" / "activity_log.json"
        data     = json.loads(log_file.read_text()) if log_file.exists() else []
        next_id  = (max(r.get("id", 0) for r in data) + 1) if data else 1
        data.append({"id": next_id, "timestamp": datetime.now().isoformat(), "date": datetime.now().strftime("%Y-%m-%d"), "time": datetime.now().strftime("%H:%M:%S"), "agent_id": agent_id, "agent_name": agent_name, "category": "life", "status": status, "summary": summary, "duration_ms": 0})
        log_file.write_text(json.dumps(data, indent=2))
    except: pass

if __name__ == "__main__":
    main()
