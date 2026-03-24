#!/usr/bin/env python3
"""
GitHub Monitor — watches jmenzies722/arvis-hq for open PRs,
failing CI runs, stale branches, and recent commits.
Reports to Telegram and broadcasts to SSE.
"""
import subprocess, json, sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path.home() / "agent-hq"
REPO = "jmenzies722/arvis-hq"

BOT_TOKEN = "8696349618:AAFsqhznbNOWoRLXZ4ugzXOEzLmaRyi9geE"
CHAT_ID   = "8743898908"

def gh(cmd):
    r = subprocess.run(["gh"] + cmd, capture_output=True, text=True)
    return r.stdout.strip()

def tg(msg):
    subprocess.run([
        "curl", "-s", "-X", "POST",
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        "-d", f"chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    ], capture_output=True)

def broadcast(msg):
    try:
        import urllib.request
        data = json.dumps({"message": msg, "type": "incoming"}).encode()
        req  = urllib.request.Request(
            "http://localhost:8766/api/log/telegram",
            data=data, headers={"Content-Type": "application/json"}, method="POST"
        )
        urllib.request.urlopen(req, timeout=3)
    except Exception:
        pass

def run():
    lines = []
    lines.append(f"*GitHub Monitor — arvis-hq*\n_{datetime.now().strftime('%b %d %H:%M')}_\n")

    # Recent commits
    commits = gh(["repo", "view", REPO, "--json", "defaultBranchRef",
                  "--jq", ".defaultBranchRef.target.history.nodes[:3][].messageHeadline"])
    if commits:
        lines.append("*Recent commits:*")
        for c in commits.split("\n")[:3]:
            lines.append(f"  • {c}")

    # Open PRs
    prs = gh(["pr", "list", "--repo", REPO, "--json", "number,title,state",
              "--jq", ".[] | \"#\" + (.number|tostring) + \" \" + .title"])
    if prs:
        lines.append(f"\n*Open PRs:*")
        for p in prs.split("\n"):
            lines.append(f"  • {p}")
    else:
        lines.append("\nNo open PRs.")

    # Recent workflow runs
    runs = gh(["run", "list", "--repo", REPO, "--limit", "3",
               "--json", "name,status,conclusion,createdAt",
               "--jq", ".[] | .name + \" — \" + (.conclusion // .status)"])
    if runs:
        lines.append(f"\n*CI Runs:*")
        for r in runs.split("\n"):
            lines.append(f"  • {r}")

    report = "\n".join(lines)
    tg(report)
    broadcast(report)
    print(report)

if __name__ == "__main__":
    run()
