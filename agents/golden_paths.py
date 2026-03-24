#!/usr/bin/env python3
"""
Golden Paths Agent
Career path agent for Platform Eng → AI Solutions Eng trajectory.
Tracks certifications, skill gaps, milestones, and next actions.
"""
import json, sys
from datetime import datetime
from pathlib import Path

BASE     = Path(__file__).parent.parent
DATA_DIR = BASE / "data"
GP_LOG   = DATA_DIR / "golden_paths.json"

ROADMAP = {
    "current_title":  "Platform Engineer",
    "target_title":   "AI Solutions Engineer",
    "comp_target":    "$300K+",
    "timeline":       "12-18 months",
    "milestones": [
        {"id": "aws_saa",       "name": "AWS SAA",           "status": "complete", "impact": "high"},
        {"id": "kiro_rollout",  "name": "Kiro rollout",       "status": "in_progress", "impact": "high"},
        {"id": "claude_ent",    "name": "Claude Enterprise",  "status": "in_progress", "impact": "high"},
        {"id": "aws_pro",       "name": "AWS Solutions Arch Pro", "status": "planned", "impact": "high"},
        {"id": "ai_eng_cert",   "name": "AI Engineering cert","status": "planned", "impact": "medium"},
        {"id": "github_port",   "name": "Public AI portfolio","status": "in_progress", "impact": "medium"},
        {"id": "comp_review",   "name": "Comp review w/ data","status": "planned", "impact": "high"},
    ],
    "skill_gaps": [
        {"skill": "LangGraph advanced",   "priority": "high"},
        {"skill": "AWS Bedrock deep dive", "priority": "high"},
        {"skill": "System design (AI)",    "priority": "high"},
        {"skill": "Startup GTM basics",    "priority": "medium"},
    ],
}

def report():
    data   = ROADMAP
    done   = [m for m in data["milestones"] if m["status"] == "complete"]
    active = [m for m in data["milestones"] if m["status"] == "in_progress"]
    next_  = [m for m in data["milestones"] if m["status"] == "planned"]

    print(f"Golden Paths — {data['current_title']} → {data['target_title']}")
    print(f"Target: {data['comp_target']} | Timeline: {data['timeline']}")
    print()
    print(f"Progress: {len(done)}/{len(data['milestones'])} milestones complete")
    print()
    print("In Progress:")
    for m in active:
        print(f"  ⚡ {m['name']}")
    print()
    print("Up Next:")
    for m in next_[:3]:
        print(f"  ○ {m['name']} [{m['impact']} impact]")
    print()
    print("Top Skill Gaps:")
    for s in data["skill_gaps"][:3]:
        print(f"  • {s['skill']} [{s['priority']}]")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    if cmd == "report":
        report()
