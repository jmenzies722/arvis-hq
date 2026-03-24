#!/usr/bin/env python3
"""
Agent HQ Server — Arvis Control Center
Serves the dashboard and provides API endpoints to trigger agents.
"""
import json, subprocess, sys, os, threading, re, queue, time
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from flask import Flask, jsonify, send_from_directory, request, Response, stream_with_context
from flask_cors import CORS

app = Flask(__name__, static_folder=str(Path.home() / "agent-hq"))
try:
    CORS(app, origins=["http://localhost:*", "http://192.168.1.178:*",
                       "https://*.vercel.app", "https://*.trycloudflare.com"])
except:
    pass

# ─── SSE Broadcaster ──────────────────────────────────────────────────────────
_sse_clients      = []          # list of queue.Queue objects, one per connected client
_sse_clients_lock = threading.Lock()

def broadcast_event(event_type, data_dict):
    """Push a typed event to every connected SSE client. Dead clients are pruned."""
    payload = {"type": event_type, "ts": datetime.now().isoformat(), **data_dict}
    msg = "data: " + json.dumps(payload) + "\n\n"
    with _sse_clients_lock:
        dead = []
        for q in _sse_clients:
            try:
                q.put_nowait(msg)
            except queue.Full:
                dead.append(q)
        for q in dead:
            _sse_clients.remove(q)

def _sse_heartbeat_thread():
    """Background thread that sends a heartbeat every 15 s to keep connections alive."""
    while True:
        time.sleep(15)
        broadcast_event("heartbeat", {})

_hb = threading.Thread(target=_sse_heartbeat_thread, daemon=True)
_hb.start()

BASE        = Path.home() / "agent-hq"
MEMORY_DIR  = Path.home() / ".claude" / "projects" / "-Users-admin" / "memory"
MEMORY_IDX  = MEMORY_DIR / "MEMORY.md"
WORKOUT_LOG = Path.home() / "workout-agent" / "logs.json"
BUDGET_LOG  = BASE / "data" / "budget.json"
SAVINGS_LOG = BASE / "data" / "savings.json"
FILE_ORG_LOG = Path.home() / "workout-agent" / "file_organizer.log"

BOT_TOKEN = "8696349618:AAFsqhznbNOWoRLXZ4ugzXOEzLmaRyi9geE"
CHAT_ID   = "8743898908"

# ─── Agent Registry ──────────────────────────────────────────────────────────
AGENTS = [
    # LIFE
    {"id": "morning_brief",   "name": "Morning Brief",    "abbr": "MB", "category": "life",   "schedule": "7:00am daily",    "status": "cloud",   "trigger_id": "trig_013pzPrWyVLkY9H8k54xzZTW", "desc": "Gmail + Calendar digest sent to Telegram every morning."},
    {"id": "night_prep",      "name": "Night Prep",       "abbr": "NP", "category": "life",   "schedule": "10:30pm daily",   "status": "cloud",   "trigger_id": "trig_01TyyZKFZEJcQnaAgS1AAKB3", "desc": "Tomorrow's schedule and priority emails, delivered before bed."},
    {"id": "pushup_tracker",  "name": "Push-Up Tracker",  "abbr": "PT", "category": "life",   "schedule": "8am + 8pm",       "status": "local",   "link": "http://192.168.1.178:8765/dashboard.html", "desc": "50 push-ups x 2 daily. Tracks sets, streak, and all-time reps."},
    {"id": "focus_session",   "name": "Focus Session",    "abbr": "FS", "category": "life",   "schedule": "On demand",       "status": "local",   "script": "agents/focus_session.py summary", "desc": "Log deep work blocks. Tracks daily focus time and notifies Telegram."},
    {"id": "habit_log",       "name": "Habit Log",        "abbr": "HL", "category": "life",   "schedule": "Daily check-in",  "status": "local",   "script": "agents/habit_log.py summary", "desc": "Daily check-in: sleep, water, gym, reading, screen-free morning."},
    {"id": "body_log",        "name": "Body Log",         "abbr": "BL", "category": "life",   "schedule": "On demand",       "status": "local",   "script": "agents/body_log.py summary", "desc": "Track weight, mood, and energy. Surfaces 7-day trends."},
    {"id": "budget_tracker",  "name": "Budget Tracker",   "abbr": "BT", "category": "life",   "schedule": "On demand",       "status": "local",   "script": "agents/budget_tracker.py summary", "desc": "Log expenses with auto-categorization. Monthly breakdown via Telegram."},
    {"id": "savings_tracker", "name": "Savings Tracker",  "abbr": "ST", "category": "life",   "schedule": "On demand",       "status": "local",   "script": "agents/savings_tracker.py status", "desc": "Progress toward SoFi $7K, Roth IRA $7K, and FXAIX $50K goals."},
    {"id": "weekly_recap",    "name": "Weekly Recap",     "abbr": "WR", "category": "life",   "schedule": "Sundays 8pm",     "status": "local",   "script": "agents/weekly_recap.py", "desc": "Full week summary: fitness, budget, savings, and wins — sent Sunday."},
    {"id": "file_organizer",  "name": "File Organizer",   "abbr": "FO", "category": "life",   "schedule": "2:00am nightly",  "status": "local",   "script": str(Path.home() / "workout-agent" / "file_organizer.py"), "desc": "Auto-sorts Downloads and Desktop into folders. Runs while you sleep."},
    {"id": "net_worth",       "name": "Net Worth",        "abbr": "NW", "category": "life",   "schedule": "On demand",       "status": "local",   "script": "agents/net_worth_tracker.py snapshot", "desc": "Track SoFi, Roth IRA, FXAIX, and total net worth with weekly delta and milestone alerts."},
    {"id": "win_log",         "name": "Win Log",          "abbr": "WL", "category": "life",   "schedule": "On demand",       "status": "local",   "script": "agents/win_log.py summary", "desc": "Log work wins at Nectar for salary negotiation, promotions, and LinkedIn content."},
    {"id": "sleep_trend",     "name": "Sleep Trend",      "abbr": "ZZ", "category": "life",   "schedule": "On demand",       "status": "local",   "script": "agents/sleep_trend.py", "desc": "7-day sleep analysis with grade and recovery insights from habit log data."},
    # WORK
    {"id": "daily_learning",  "name": "Daily Learning",   "abbr": "DL", "category": "work",   "schedule": "9:00am daily",    "status": "cloud",   "trigger_id": "trig_01Eu4ufTk1JjbdqbksNPwmni", "desc": "One focused AWS, AI, or DevOps lesson researched fresh each morning."},
    {"id": "standup",         "name": "Standup",          "abbr": "SU", "category": "work",   "schedule": "9am weekdays",    "status": "local",   "script": "agents/standup.py", "desc": "Auto-generates standup from recent git commits across your repos."},
    {"id": "interview_prep",  "name": "Interview Prep",   "abbr": "IP", "category": "work",   "schedule": "Daily",           "status": "local",   "script": "agents/interview_prep.py today", "desc": "Daily AWS/AI/system design question. 43-question bank covering SAA, DevOps, and behavioral."},
    {"id": "job_tracker",     "name": "Job Tracker",       "abbr": "JT", "category": "work",   "schedule": "Daily",           "status": "local",   "script": "agents/job_tracker.py status", "desc": "Tracks job opportunities matching Platform Eng → AI Solutions Eng. Monitors role requirements and gaps."},
    {"id": "cluster_monitor", "name": "Cluster Monitor",   "abbr": "CM", "category": "work",   "schedule": "Hourly",          "status": "local",   "script": "agents/cluster_monitor.py status", "desc": "Monitors home cluster health, uptime, and resource utilization. Alerts on anomalies."},
    {"id": "golden_paths",    "name": "Golden Paths",      "abbr": "GP", "category": "work",   "schedule": "Weekly",          "status": "local",   "script": "agents/golden_paths.py report", "desc": "Career path agent. Tracks Platform Eng → AI Solutions Eng trajectory, gaps, certs, next actions."},
    {"id": "learning_platform","name": "Learning Platform","abbr": "LP", "category": "work",   "schedule": "Daily",           "status": "local",   "script": "agents/learning_platform.py today", "desc": "Correlates learning resources to AI Solutions Eng job requirements. Builds your personalized roadmap."},
    {"id": "big_brain",       "name": "Big Brain",         "abbr": "BB", "category": "work",   "schedule": "On demand",       "status": "local",   "script": "agents/big_brain.py run", "desc": "Meta-orchestration agent. Knows your goals, coordinates all agents, surfaces priorities and blockers."},
    {"id": "github_monitor",  "name": "GitHub Monitor",    "abbr": "GH", "category": "work",   "schedule": "On demand",       "status": "local",   "script": "agents/github_monitor.py", "desc": "Monitors arvis-hq for open PRs, CI runs, and recent commits. Reports to Telegram."},
    # INCOME
    {"id": "callbrief",       "name": "CallBrief",        "abbr": "CB", "category": "income", "schedule": "Always on :8767", "status": "local",   "link": "http://192.168.1.178:8767", "desc": "AI call summarizer SaaS. Paste transcript, get structured brief + actions."},
    {"id": "startup_hq",      "name": "Startup HQ",       "abbr": "SH", "category": "income", "schedule": "On demand",       "status": "local",   "link": "http://192.168.1.178:8768", "desc": "Startup pipeline, market research, and decision log. 7 opportunities tracked."},
]

FOCUS_LOG  = BASE / "data" / "focus_log.json"
HABIT_LOG  = BASE / "data" / "habit_log.json"
BODY_LOG   = BASE / "data" / "body_log.json"

# ─── Helpers ─────────────────────────────────────────────────────────────────
def load_json(path):
    try:
        return json.loads(Path(path).read_text())
    except:
        return []

def get_workout_stats():
    logs = load_json(WORKOUT_LOG)
    daily = defaultdict(int)
    for l in logs:
        daily[l["date"]] += l["total_reps"]
    today = datetime.now().strftime("%Y-%m-%d")
    streak = 0
    check = datetime.now().date()
    while True:
        d = check.strftime("%Y-%m-%d")
        if daily.get(d, 0) > 0:
            streak += 1
            check -= timedelta(days=1)
        else:
            break
    return {
        "today": daily.get(today, 0),
        "streak": streak,
        "total": sum(l["total_reps"] for l in logs),
        "sessions": len(logs),
    }

def run_script_async(script_path, agent_id="unknown", agent_name="Agent"):
    def _run():
        sys.path.insert(0, str(BASE / "agents"))
        from arvis_logger import log_event
        start = time.time()
        log_event(agent_id, agent_name, "running", "Triggered from dashboard", 0)
        broadcast_event("agent_run", {"agent": agent_name, "status": "running"})
        try:
            parts = script_path.split()
            result = subprocess.run(["python3"] + parts, cwd=str(BASE), timeout=60, capture_output=True, text=True)
            ms = int((time.time() - start) * 1000)
            summary = result.stdout.strip().split("\n")[0][:120] if result.stdout.strip() else "Completed"
            status = "success" if result.returncode == 0 else "error"
            log_event(agent_id, agent_name, status, summary, ms)
            broadcast_event("agent_done", {"agent": agent_name, "status": status, "summary": summary})
        except Exception as e:
            ms = int((time.time() - start) * 1000)
            log_event(agent_id, agent_name, "error", str(e)[:120], ms)
            broadcast_event("agent_done", {"agent": agent_name, "status": "error", "summary": str(e)[:120]})
    t = threading.Thread(target=_run, daemon=True)
    t.start()

# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route("/api/stream")
def sse_stream():
    """Server-Sent Events endpoint. Clients subscribe here for live updates."""
    client_q = queue.Queue(maxsize=64)
    with _sse_clients_lock:
        _sse_clients.append(client_q)

    @stream_with_context
    def generate():
        # Send a connection-acknowledged event immediately
        connected_msg = "data: " + json.dumps({"type": "connected", "ts": datetime.now().isoformat()}) + "\n\n"
        yield connected_msg
        try:
            while True:
                try:
                    msg = client_q.get(timeout=20)
                    yield msg
                except queue.Empty:
                    # Send a keep-alive comment to prevent proxy timeouts
                    yield ": ping\n\n"
        except GeneratorExit:
            pass
        finally:
            with _sse_clients_lock:
                if client_q in _sse_clients:
                    _sse_clients.remove(client_q)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":  "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":     "keep-alive",
        }
    )

@app.route("/api/log/telegram", methods=["POST"])
def log_telegram():
    """Log a Telegram message to the live Command Center feed."""
    body    = request.get_json() or {}
    message = body.get("message", "").strip()
    msg_type = body.get("type", "incoming")  # "incoming" | "outgoing"

    if not message:
        return jsonify({"ok": False, "error": "message is required"}), 400

    if msg_type == "outgoing":
        broadcast_event("telegram_out", {"text": message})
    else:
        broadcast_event("telegram_in", {"text": message})

    return jsonify({"ok": True})

@app.route("/")
def index():
    return send_from_directory(str(BASE), "index.html")

@app.route("/api/status")
def api_status():
    ws = get_workout_stats()
    active = sum(1 for a in AGENTS if a["status"] in ("local", "cloud"))
    cloud  = sum(1 for a in AGENTS if a["status"] == "cloud")
    return jsonify({
        "agents": AGENTS,
        "workout": ws,
        "active_count": active,
        "cloud_count": cloud,
        "timestamp": datetime.now().isoformat(),
    })

@app.route("/api/run/<agent_id>", methods=["POST"])
def run_agent(agent_id):
    agent = next((a for a in AGENTS if a["id"] == agent_id), None)
    if not agent:
        return jsonify({"ok": False, "error": "Agent not found"}), 404
    if agent["status"] == "pending":
        return jsonify({"ok": False, "error": "Agent pending setup"}), 400

    if agent.get("script"):
        run_script_async(agent["script"], agent["id"], agent["name"])
        return jsonify({"ok": True, "message": f"{agent['name']} triggered"})
    elif agent.get("link"):
        broadcast_event("agent_run", {"agent": agent["name"], "status": "opened"})
        return jsonify({"ok": True, "message": "Open dashboard link", "link": agent["link"]})
    elif agent.get("trigger_id"):
        # Route cloud agents to their real scripts
        cloud_script_map = {
            "morning_brief": "cloud_agents/morning_brief.py",
            "night_prep":    "cloud_agents/night_prep.py",
            "daily_learning":"cloud_agents/daily_learning.py",
        }
        script = cloud_script_map.get(agent_id)
        if script and (BASE / script).exists():
            run_script_async(script, agent["id"], agent["name"])
            return jsonify({"ok": True, "message": f"{agent['name']} triggered"})
        return jsonify({"ok": True, "message": f"{agent['name']} is a cloud agent — runs on schedule", "schedule": agent["schedule"]})
    return jsonify({"ok": False, "error": "No trigger configured"}), 400

@app.route("/api/activity")
def api_activity():
    sys.path.insert(0, str(BASE / "agents"))
    try:
        from arvis_logger import ACTIVITY_LOG
        events = json.loads(Path(ACTIVITY_LOG).read_text()) if Path(ACTIVITY_LOG).exists() else []
        # Stats per agent
        from collections import defaultdict
        stats = defaultdict(lambda: {"runs": 0, "success": 0, "error": 0, "last_run": None, "avg_ms": 0, "total_ms": 0})
        for e in events:
            aid = e["agent_id"]
            stats[aid]["runs"] += 1
            if e["status"] == "success": stats[aid]["success"] += 1
            if e["status"] == "error":   stats[aid]["error"] += 1
            if not stats[aid]["last_run"] or e["timestamp"] > stats[aid]["last_run"]:
                stats[aid]["last_run"] = e["timestamp"]
            stats[aid]["total_ms"] += e.get("duration_ms", 0)
        for aid in stats:
            runs = stats[aid]["runs"]
            stats[aid]["avg_ms"] = int(stats[aid]["total_ms"] / runs) if runs > 0 else 0
            del stats[aid]["total_ms"]
        return jsonify({
            "events": list(reversed(events[-50:])),  # last 50, newest first
            "stats": dict(stats),
            "total_runs": len(events),
        })
    except Exception as e:
        return jsonify({"events": [], "stats": {}, "total_runs": 0, "error": str(e)})

@app.route("/api/audit")
def api_audit():
    """Health check for every agent — last run, next scheduled run, status."""
    import subprocess as sp
    from datetime import datetime
    try:
        log_file = BASE / "data" / "activity_log.json"
        events   = json.loads(log_file.read_text()) if log_file.exists() else []
    except:
        events = []

    last_run_map = {}
    status_map   = {}
    for e in events:
        aid = e.get("agent_id")
        if aid and (aid not in last_run_map or e["timestamp"] > last_run_map[aid]):
            last_run_map[aid] = e["timestamp"]
            status_map[aid]   = e.get("status", "unknown")

    # Which local scripts actually exist and execute
    CLOUD_SCRIPTS = {
        "morning_brief":  "cloud_agents/morning_brief.py",
        "night_prep":     "cloud_agents/night_prep.py",
        "daily_learning": "cloud_agents/daily_learning.py",
    }
    audit = []
    for a in AGENTS:
        aid    = a["id"]
        script = a.get("script") or CLOUD_SCRIPTS.get(aid)
        executable = False
        if script:
            script_file = script.split()[0]  # strip args
            path = BASE / script_file if not script_file.startswith("/") else Path(script_file)
            executable = path.exists()
        elif a.get("link"):
            executable = True  # link-based, assume live

        audit.append({
            "id":          aid,
            "name":        a["name"],
            "category":    a["category"],
            "schedule":    a["schedule"],
            "status":      a["status"],
            "executable":  executable,
            "last_run":    last_run_map.get(aid),
            "last_status": status_map.get(aid, "never"),
            "has_script":  bool(script),
        })
    return jsonify({"agents": audit, "total": len(audit)})

@app.route("/api/log/expense", methods=["POST"])
def log_expense():
    body   = request.get_json() or {}
    amount = body.get("amount", 0)
    note   = body.get("note", "")
    run_script_async(f"agents/budget_tracker.py log {amount} {note}", "budget_tracker", "Budget Tracker")
    broadcast_event("metric_update", {"key": "spent_today", "value": float(amount)})
    return jsonify({"ok": True})

@app.route("/api/log/workout", methods=["POST"])
def log_workout():
    body    = request.get_json() or {}
    sets    = body.get("sets", 1)
    reps    = body.get("reps", 50)
    session = body.get("session", "manual")
    script  = str(Path.home() / "workout-agent" / f"log_workout.py {sets} {reps} {session}")
    run_script_async(script, "pushup_tracker", "Push-Up Tracker")
    total_reps = int(sets) * int(reps)
    broadcast_event("metric_update", {"key": "pushups_today", "value": total_reps})
    return jsonify({"ok": True})

@app.route("/api/log/focus", methods=["POST"])
def log_focus():
    body     = request.get_json() or {}
    duration = body.get("duration_min", 25)
    goal     = body.get("goal", "Deep work")
    run_script_async(f"agents/focus_session.py {duration} {goal}", "focus_session", "Focus Session")
    broadcast_event("metric_update", {"key": "focus_min", "value": int(duration)})
    return jsonify({"ok": True})

@app.route("/api/log/habit", methods=["POST"])
def log_habit():
    body    = request.get_json() or {}
    sleep   = body.get("sleep_hours", 7)
    water   = body.get("water_glasses", 8)
    gym     = "yes" if body.get("gym", False) else "no"
    reading = body.get("reading_min", 0)
    phone   = "yes" if body.get("no_phone_am", False) else "no"
    run_script_async(f"agents/habit_log.py {sleep} {water} {gym} {reading} {phone}", "habit_log", "Habit Log")
    return jsonify({"ok": True})

@app.route("/api/log/body", methods=["POST"])
def log_body():
    body   = request.get_json() or {}
    weight = body.get("weight_lbs", 0)
    mood   = body.get("mood", 3)
    energy = body.get("energy", 3)
    run_script_async(f"agents/body_log.py {weight} {mood} {energy}", "body_log", "Body Log")
    return jsonify({"ok": True})

@app.route("/api/log/net_worth", methods=["POST"])
def log_net_worth():
    body    = request.get_json() or {}
    account = body.get("account", "")
    amount  = body.get("amount", 0)
    run_script_async(f"agents/net_worth_tracker.py update {account} {amount}", "net_worth", "Net Worth")
    broadcast_event("metric_update", {"key": account, "value": float(amount)})
    return jsonify({"ok": True})

@app.route("/api/log/win", methods=["POST"])
def log_win():
    body     = request.get_json() or {}
    category = body.get("category", "personal")
    desc     = body.get("description", "")
    run_script_async(f"agents/win_log.py log {category} {desc}", "win_log", "Win Log")
    return jsonify({"ok": True})

@app.route("/api/today")
def api_today():
    ws      = get_workout_stats()
    # Focus today
    try:
        focus_entries = json.loads(Path(FOCUS_LOG).read_text()) if Path(FOCUS_LOG).exists() else []
        today_str     = datetime.now().strftime("%Y-%m-%d")
        focus_today   = [f for f in focus_entries if f["date"] == today_str]
        focus_min     = sum(f["duration_min"] for f in focus_today)
    except:
        focus_min, focus_today = 0, []
    # Habit today
    try:
        habit_entries = json.loads(Path(HABIT_LOG).read_text()) if Path(HABIT_LOG).exists() else []
        today_str     = datetime.now().strftime("%Y-%m-%d")
        habit_today   = next((h for h in habit_entries if h["date"] == today_str), None)
    except:
        habit_today   = None
    # Budget today
    try:
        budget_entries = json.loads(Path(BUDGET_LOG).read_text()) if Path(BUDGET_LOG).exists() else []
        today_str      = datetime.now().strftime("%Y-%m-%d")
        spent_today    = sum(float(e.get("amount", 0)) for e in budget_entries if e.get("date", "") == today_str)
    except:
        spent_today    = 0
    # Activity runs today
    try:
        sys.path.insert(0, str(BASE / "agents"))
        from arvis_logger import ACTIVITY_LOG
        activity = json.loads(Path(ACTIVITY_LOG).read_text()) if Path(ACTIVITY_LOG).exists() else []
        today_str = datetime.now().strftime("%Y-%m-%d")
        runs_today = len([a for a in activity if a.get("timestamp", "").startswith(today_str)])
    except:
        runs_today = 0
    return jsonify({
        "date": datetime.now().strftime("%A, %B %-d"),
        "pushups_today": ws["today"],
        "streak": ws["streak"],
        "focus_min_today": focus_min,
        "focus_sessions_today": len(focus_today),
        "spent_today": round(spent_today, 2),
        "habit_today": habit_today,
        "runs_today": runs_today,
        "timestamp": datetime.now().isoformat(),
    })

# ─── Memory API ──────────────────────────────────────────────────────────────
def parse_memory_file(path: Path):
    """Parse a memory markdown file with YAML frontmatter."""
    try:
        text  = path.read_text()
        name  = path.stem
        mtype = "user"
        desc  = ""
        body  = text
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                fm   = parts[1]
                body = parts[2].strip()
                for line in fm.splitlines():
                    if line.startswith("name:"):
                        name = line.split(":", 1)[1].strip()
                    elif line.startswith("type:"):
                        mtype = line.split(":", 1)[1].strip()
                    elif line.startswith("description:"):
                        desc = line.split(":", 1)[1].strip()
        return {
            "file":        path.name,
            "name":        name,
            "type":        mtype,
            "description": desc,
            "body":        body,
            "updated":     datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
        }
    except Exception as e:
        return None

@app.route("/api/memory", methods=["GET"])
def get_memory():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    memories = []
    for f in sorted(MEMORY_DIR.glob("*.md")):
        if f.name == "MEMORY.md":
            continue
        m = parse_memory_file(f)
        if m:
            memories.append(m)
    return jsonify({"memories": memories, "count": len(memories)})

@app.route("/api/memory", methods=["POST"])
def add_memory():
    body  = request.get_json() or {}
    name  = re.sub(r"[^a-z0-9_]", "_", body.get("name", "untitled").lower().strip())[:40]
    mtype = body.get("type", "user")
    desc  = body.get("description", "")
    text  = body.get("body", "").strip()
    if not text:
        return jsonify({"ok": False, "error": "body is required"}), 400

    filename = f"{name}.md"
    filepath = MEMORY_DIR / filename
    # Avoid clobbering — add suffix if exists
    if filepath.exists():
        filename = f"{name}_{int(datetime.now().timestamp())}.md"
        filepath = MEMORY_DIR / filename

    content = f"""---
name: {name}
description: {desc}
type: {mtype}
---

{text}
"""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content)

    # Update MEMORY.md index
    _rebuild_memory_index()

    return jsonify({"ok": True, "file": filename})

@app.route("/api/memory/<filename>", methods=["PUT"])
def update_memory(filename):
    body     = request.get_json() or {}
    filepath = MEMORY_DIR / filename
    if not filepath.exists():
        return jsonify({"ok": False, "error": "Not found"}), 404
    m = parse_memory_file(filepath)
    if not m:
        return jsonify({"ok": False, "error": "Parse error"}), 500

    new_type = body.get("type", m["type"])
    new_desc = body.get("description", m["description"])
    new_body = body.get("body", m["body"]).strip()

    content = f"""---
name: {m["name"]}
description: {new_desc}
type: {new_type}
---

{new_body}
"""
    filepath.write_text(content)
    _rebuild_memory_index()
    return jsonify({"ok": True})

@app.route("/api/memory/<filename>", methods=["DELETE"])
def delete_memory(filename):
    filepath = MEMORY_DIR / filename
    if not filepath.exists():
        return jsonify({"ok": False, "error": "Not found"}), 404
    filepath.unlink()
    _rebuild_memory_index()
    return jsonify({"ok": True})

def _rebuild_memory_index():
    """Regenerate MEMORY.md from all memory files."""
    entries = []
    for f in sorted(MEMORY_DIR.glob("*.md")):
        if f.name == "MEMORY.md":
            continue
        m = parse_memory_file(f)
        if m:
            entries.append(f"- [{f.name}]({f.name}) — {m['description'] or m['name']}")
    MEMORY_IDX.write_text("# Memory Index\n\n" + "\n".join(entries) + "\n")


REMINDERS_CACHE = BASE / "data" / "reminders_cache.json"

def _refresh_reminders_cache():
    """Background thread: pull Apple Reminders every 15 min and write to cache file."""
    script = (
        'tell application "Reminders"\n'
        '  set output to ""\n'
        '  repeat with theList in lists\n'
        '    set lName to name of theList\n'
        '    repeat with r in (reminders of theList whose completed is false)\n'
        '      set rDue to ""\n'
        '      try\n'
        '        set rDue to due date of r as string\n'
        '      end try\n'
        '      set output to output & lName & "||" & (name of r) & "||" & rDue & "~~"\n'
        '    end repeat\n'
        '  end repeat\n'
        '  return output\n'
        'end tell'
    )
    while True:
        try:
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=90)
            raw    = result.stdout.strip()
            items  = []
            for chunk in raw.split("~~"):
                chunk = chunk.strip()
                if not chunk:
                    continue
                parts = chunk.split("||")
                if len(parts) >= 2:
                    items.append({
                        "list": parts[0].strip(),
                        "name": parts[1].strip(),
                        "due":  parts[2].strip() if len(parts) > 2 else "",
                    })
            REMINDERS_CACHE.write_text(json.dumps({"reminders": items, "updated": datetime.now().isoformat()}))
        except Exception:
            pass
        time.sleep(900)  # refresh every 15 minutes

_rem_thread = threading.Thread(target=_refresh_reminders_cache, daemon=True)
_rem_thread.start()

@app.route("/api/reminders")
def api_reminders():
    try:
        data = json.loads(REMINDERS_CACHE.read_text()) if REMINDERS_CACHE.exists() else {}
        items = data.get("reminders", [])
        return jsonify({"reminders": items, "count": len(items), "updated": data.get("updated", "")})
    except Exception as e:
        return jsonify({"reminders": [], "count": 0, "error": str(e)})


@app.route("/api/charts")
def api_charts():
    from datetime import date
    today = datetime.now().date()

    # 7-day push-up data
    logs = load_json(WORKOUT_LOG)
    daily_pushups = defaultdict(int)
    for l in logs:
        daily_pushups[l["date"]] += l.get("total_reps", 0)
    weekdays = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    pushup_7d = []
    for i in range(6, -1, -1):
        d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        pushup_7d.append({"date": d, "label": weekdays[(today - timedelta(days=i)).weekday()], "reps": daily_pushups.get(d, 0)})

    # Savings / net worth
    nw_entries = load_json(BASE / "data" / "net_worth.json")
    if not isinstance(nw_entries, list):
        nw_entries = []
    by_acct = {}
    for e in nw_entries:
        by_acct[e.get("account", "")] = e.get("amount", 0)
    savings_goals = [
        {"id": "sofi",  "label": "SoFi",     "balance": by_acct.get("sofi",  0), "goal": 7000},
        {"id": "roth",  "label": "Roth IRA",  "balance": by_acct.get("roth",  0), "goal": 7000},
        {"id": "fxaix", "label": "FXAIX",     "balance": by_acct.get("fxaix", 0), "goal": 50000},
    ]
    total_nw = sum(by_acct.values())

    # 7-day agent run counts
    try:
        sys.path.insert(0, str(BASE / "agents"))
        from arvis_logger import ACTIVITY_LOG as _ALOG
        activity = load_json(Path(_ALOG)) if Path(_ALOG).exists() else []
    except Exception:
        activity = []
    runs_by_day = defaultdict(int)
    for e in activity:
        d = e.get("timestamp", "")[:10]
        if d:
            runs_by_day[d] += 1
    runs_7d = []
    for i in range(6, -1, -1):
        d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        runs_7d.append({"date": d, "label": weekdays[(today - timedelta(days=i)).weekday()], "runs": runs_by_day.get(d, 0)})

    return jsonify({
        "pushup_7d":    pushup_7d,
        "savings":      savings_goals,
        "total_nw":     total_nw,
        "agent_runs_7d": runs_7d,
    })


@app.route("/api/deploy", methods=["POST"])
def api_deploy():
    """git pull + restart — callable from Telegram via Claude Code."""
    try:
        result = subprocess.run(
            ["git", "pull", "origin", "main"],
            capture_output=True, text=True, cwd=str(BASE), timeout=30
        )
        output = (result.stdout + result.stderr).strip()
        already_latest = "Already up to date" in output

        broadcast_event("agent_run", {"agent": "deploy", "message": f"Deploy: {output[:120]}"})

        if not already_latest:
            # Restart server in background thread after response is sent
            def _restart():
                time.sleep(1.5)
                os.execv(sys.executable, [sys.executable] + sys.argv)
            threading.Thread(target=_restart, daemon=True).start()

        return jsonify({"ok": True, "output": output, "restarting": not already_latest})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    print("Agent HQ starting on http://0.0.0.0:8766")
    app.run(host="0.0.0.0", port=8766, debug=False)
