#!/usr/bin/env python3
"""
Morning Brief — pulls Calendar, Reminders, and today's focus, sends to Telegram.
Runs daily at 7:00am via cron. Also triggerable on demand.
"""
import subprocess, json, sys, urllib.request, urllib.parse
from datetime import datetime
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

def get_calendar():
    script = '''
tell application "Calendar"
  set todayStart to current date
  set hours of todayStart to 0
  set minutes of todayStart to 0
  set seconds of todayStart to 0
  set todayEnd to todayStart + 86399
  set output to ""
  repeat with c in calendars
    try
      repeat with e in (events of c whose start date >= todayStart and start date <= todayEnd)
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

def get_reminders():
    script = '''
tell application "Reminders"
  set output to ""
  repeat with r in (reminders whose completed is false)
    set output to output & "• " & (name of r) & "\n"
  end repeat
  return output
end tell'''
    return applescript(script)

def get_todays_wins():
    """Pull any wins logged today for morning motivation."""
    wins_file = BASE / "data" / "wins.json"
    if not wins_file.exists():
        return ""
    try:
        data  = json.loads(wins_file.read_text())
        today = datetime.now().strftime("%Y-%m-%d")
        wins  = [w for w in data.get("wins", []) if w.get("date", "").startswith(today)]
        return "\n".join(f"• {w['description']}" for w in wins[-3:])
    except:
        return ""

def get_habit_streak():
    """Check current push-up streak."""
    habit_file = BASE / "data" / "workout_log.json"
    if not habit_file.exists():
        return 0
    try:
        data = json.loads(habit_file.read_text())
        return data.get("streak", 0)
    except:
        return 0

def broadcast_to_hq(message, msg_type="outgoing"):
    """Push this agent's output to the Command Center live feed."""
    try:
        url  = "http://localhost:8766/api/log/telegram"
        data = json.dumps({"message": message[:300], "type": msg_type}).encode()
        req  = urllib.request.Request(url, data, {"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=3)
    except Exception:
        pass

def main():
    day  = datetime.now().strftime("%A, %b %-d")
    hour = datetime.now().hour

    greeting = "Good morning" if hour < 12 else "Hey"
    lines    = [f"☀️ {greeting}, Josh — {day}\n{'─'*28}"]

    # Calendar
    cal = get_calendar()
    if cal.strip():
        lines.append("\n📅 Today's Schedule")
        for ln in cal.strip().splitlines():
            if ln.strip():
                lines.append(f"  {ln.strip()}")
    else:
        lines.append("\n📅 Nothing scheduled — good day to ship something.")

    # Reminders
    rem = get_reminders()
    if rem.strip():
        lines.append("\n🔔 Reminders")
        for ln in rem.strip().splitlines()[:5]:
            if ln.strip():
                lines.append(f"  {ln.strip()}")

    # Streak
    streak = get_habit_streak()
    if streak > 0:
        lines.append(f"\n🔥 Push-Up Streak: {streak} days — keep it going")

    # Priorities
    lines.append("\n🎯 Top Priorities")
    lines.append("  • Kiro rollout — log any new evidence for Seth/Mike")
    lines.append("  • Claude Enterprise — move one piece forward today")
    lines.append("  • Log a win if you ship anything (win command)")

    lines.append("\n— Arvis")

    msg = "\n".join(lines)
    tg(msg)
    print(msg)
    broadcast_to_hq(f"Morning Brief sent — {day}", "outgoing")

    # Log to activity
    log_run("morning_brief", "Morning Brief", "success", f"Sent morning brief for {day}")

def log_run(agent_id, agent_name, status, summary):
    try:
        log_file = BASE / "data" / "activity_log.json"
        data     = json.loads(log_file.read_text()) if log_file.exists() else []
        next_id  = (max(r.get("id", 0) for r in data) + 1) if data else 1
        data.append({
            "id": next_id,
            "timestamp": datetime.now().isoformat(),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M:%S"),
            "agent_id": agent_id,
            "agent_name": agent_name,
            "category": "life",
            "status": status,
            "summary": summary,
            "duration_ms": 0,
        })
        log_file.write_text(json.dumps(data, indent=2))
    except:
        pass

if __name__ == "__main__":
    main()
