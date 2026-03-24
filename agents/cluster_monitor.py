#!/usr/bin/env python3
"""
Cluster Monitor Agent
Monitors home cluster health, uptime, and resource utilization.
Reports anomalies and service status to Telegram.
"""
import json, sys, subprocess
from datetime import datetime
from pathlib import Path

BASE      = Path(__file__).parent.parent
DATA_DIR  = BASE / "data"
CLUSTER_LOG = DATA_DIR / "cluster_monitor.json"

# Configure your cluster nodes here
NODES = [
    {"name": "Mac (local)",   "host": "localhost",       "type": "mac"},
    # Add more: {"name": "Pi", "host": "192.168.1.x", "type": "linux"},
]

SERVICES = [
    {"name": "Agent HQ",     "url": "http://localhost:8766/api/status"},
    {"name": "Startup HQ",   "url": "http://localhost:8768"},
    {"name": "CallBrief",    "url": "http://localhost:8767"},
]

def ping(host):
    try:
        r = subprocess.run(["ping", "-c", "1", "-W", "1", host], capture_output=True, timeout=3)
        return r.returncode == 0
    except Exception:
        return False

def check_service(url):
    try:
        import urllib.request
        urllib.request.urlopen(url, timeout=3)
        return "up"
    except Exception:
        return "down"

def status():
    results = []
    print("Cluster Monitor — Status Check")
    print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
    print()

    for svc in SERVICES:
        state = check_service(svc["url"])
        icon  = "✓" if state == "up" else "✗"
        print(f"  {icon} {svc['name']}: {state}")
        results.append({"name": svc["name"], "status": state, "ts": datetime.now().isoformat()})

    # Save snapshot
    DATA_DIR.mkdir(exist_ok=True)
    log = json.loads(CLUSTER_LOG.read_text()) if CLUSTER_LOG.exists() else {"snapshots": []}
    log["snapshots"].append({"ts": datetime.now().isoformat(), "services": results})
    log["snapshots"] = log["snapshots"][-100:]  # keep last 100
    CLUSTER_LOG.write_text(json.dumps(log, indent=2))

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        status()
