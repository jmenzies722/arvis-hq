#!/usr/bin/env python3
"""
Arvis Central Activity Logger
All agents import and call this to log their runs centrally.
"""
import json, time
from datetime import datetime
from pathlib import Path

ACTIVITY_LOG = Path.home() / "agent-hq" / "data" / "activity_log.json"
MAX_ENTRIES = 500  # keep last 500 events

def log_event(agent_id, agent_name, status, summary="", duration_ms=0, category=""):
    """
    Log an agent run event.
    status: "success" | "error" | "running" | "skipped"
    """
    ACTIVITY_LOG.parent.mkdir(parents=True, exist_ok=True)
    try:
        existing = json.loads(ACTIVITY_LOG.read_text()) if ACTIVITY_LOG.exists() else []
    except:
        existing = []

    entry = {
        "id": len(existing) + 1,
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M:%S"),
        "agent_id": agent_id,
        "agent_name": agent_name,
        "category": category,
        "status": status,
        "summary": summary,
        "duration_ms": duration_ms,
    }
    existing.append(entry)
    # Keep only last MAX_ENTRIES
    if len(existing) > MAX_ENTRIES:
        existing = existing[-MAX_ENTRIES:]
    ACTIVITY_LOG.write_text(json.dumps(existing, indent=2))
    return entry


def timed_run(agent_id, agent_name, category=""):
    """Context manager for timing + logging agent runs."""
    import time
    class Timer:
        def __enter__(self):
            self.start = time.time()
            log_event(agent_id, agent_name, "running", "Agent started", 0, category)
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            ms = int((time.time() - self.start) * 1000)
            if exc_type:
                log_event(agent_id, agent_name, "error", str(exc_val)[:200], ms, category)
            else:
                log_event(agent_id, agent_name, "success", self.summary if hasattr(self, 'summary') else "Completed", ms, category)
        def set_summary(self, s):
            self.summary = s
    return Timer()
