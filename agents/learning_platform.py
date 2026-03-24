#!/usr/bin/env python3
"""
Learning Platform Agent
Correlates learning resources to AI Solutions Eng job requirements.
Builds personalized roadmap from current skills to target role.
"""
import json, sys
from datetime import datetime
from pathlib import Path

BASE      = Path(__file__).parent.parent
DATA_DIR  = BASE / "data"
LP_LOG    = DATA_DIR / "learning_platform.json"

LEARNING_MAP = [
    {
        "skill": "AWS Bedrock + Claude API",
        "priority": 1,
        "resources": ["AWS Bedrock docs", "Anthropic API cookbook", "Daily Learning agent"],
        "job_relevance": "Core requirement for AI Solutions Eng roles",
        "estimated_hours": 20,
        "status": "in_progress",
    },
    {
        "skill": "LangGraph / Agent Orchestration",
        "priority": 2,
        "resources": ["LangGraph docs", "LangChain Academy", "CrewAI tutorials"],
        "job_relevance": "Required for multi-agent system design",
        "estimated_hours": 30,
        "status": "in_progress",
    },
    {
        "skill": "AWS Solutions Architect Pro",
        "priority": 3,
        "resources": ["A Cloud Guru", "AWS practice exams", "Whitepapers"],
        "job_relevance": "Credential differentiator, required at senior level",
        "estimated_hours": 80,
        "status": "planned",
    },
    {
        "skill": "System Design (AI-focused)",
        "priority": 4,
        "resources": ["Designing ML Systems (book)", "ByteByteGo", "AI system design patterns"],
        "job_relevance": "Technical interview requirement",
        "estimated_hours": 40,
        "status": "planned",
    },
    {
        "skill": "MLOps + Model Deployment",
        "priority": 5,
        "resources": ["SageMaker docs", "MLflow", "AWS ML blog"],
        "job_relevance": "Differentiator for senior AI roles",
        "estimated_hours": 30,
        "status": "planned",
    },
]

def today():
    active = [s for s in LEARNING_MAP if s["status"] == "in_progress"]
    if not active:
        print("No active learning tracks. Start one with: learning_platform.py start <skill_id>")
        return
    current = active[0]
    print(f"Learning Platform — Today's Focus")
    print(f"Track: {current['skill']}")
    print(f"Why: {current['job_relevance']}")
    print(f"Resources: {', '.join(current['resources'][:2])}")
    print()
    print("Your roadmap:")
    for i, s in enumerate(LEARNING_MAP[:5], 1):
        icon = "✓" if s["status"] == "complete" else "⚡" if s["status"] == "in_progress" else "○"
        print(f"  {icon} {i}. {s['skill']} (~{s['estimated_hours']}h)")

def status():
    today()

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "today"
    if cmd in ("today", "status"):
        today()
