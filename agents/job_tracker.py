#!/usr/bin/env python3
"""
Job Tracker Agent
Tracks job opportunities matching Platform Eng → AI Solutions Eng trajectory.
Monitors role requirements, highlights skill gaps, surfaces new openings.
"""
import json, sys
from datetime import datetime
from pathlib import Path

BASE     = Path(__file__).parent.parent
DATA_DIR = BASE / "data"
JOB_LOG  = DATA_DIR / "job_tracker.json"

TARGET_TITLES = [
    "AI Solutions Engineer",
    "Platform Engineer",
    "AI Infrastructure Engineer",
    "MLOps Engineer",
    "DevOps AI Engineer",
    "Technical Co-Founder",
]

KEY_SKILLS = ["AWS", "Claude API", "LangGraph", "Terraform", "Kubernetes", "Python", "AI/ML", "Platform Engineering"]

def load_jobs():
    if JOB_LOG.exists():
        return json.loads(JOB_LOG.read_text())
    return {"opportunities": [], "last_scan": None}

def save_jobs(data):
    DATA_DIR.mkdir(exist_ok=True)
    JOB_LOG.write_text(json.dumps(data, indent=2))

def status():
    data = load_jobs()
    opps = data.get("opportunities", [])
    active = [o for o in opps if o.get("status") == "active"]
    print(f"Job Tracker — {len(active)} active opportunities")
    print(f"Target titles: {', '.join(TARGET_TITLES[:3])}...")
    if active:
        for o in active[:5]:
            print(f"  • {o.get('title')} @ {o.get('company')} [{o.get('status')}]")
    else:
        print("  No opportunities logged yet.")
        print("  Add one: job_tracker.py add 'Title' 'Company' 'URL'")

def add_opportunity(title, company, url=""):
    data = load_jobs()
    data["opportunities"].append({
        "id": len(data["opportunities"]) + 1,
        "title": title,
        "company": company,
        "url": url,
        "status": "active",
        "added": datetime.now().isoformat(),
        "notes": "",
    })
    save_jobs(data)
    print(f"Added: {title} @ {company}")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        status()
    elif cmd == "add" and len(sys.argv) >= 4:
        add_opportunity(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "")
    else:
        status()
