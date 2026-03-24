#!/usr/bin/env python3
"""
Daily Standup Generator
Pulls recent git activity + sends a formatted standup to Telegram
"""
import subprocess, urllib.request, urllib.parse, os, sys
from datetime import datetime, timedelta
from pathlib import Path

BOT_TOKEN = "8696349618:AAFsqhznbNOWoRLXZ4ugzXOEzLmaRyi9geE"
CHAT_ID = "8743898908"

# Repo paths to scan for git activity
REPO_PATHS = [
    Path.home() / "code",
    Path.home() / "Documents",
    Path.home() / "Developer",
    Path.home(),
]

def get_git_repos():
    repos = []
    for base in REPO_PATHS:
        if not base.exists():
            continue
        # Direct git repo
        if (base / ".git").exists():
            repos.append(base)
        # One level deep
        for child in base.iterdir():
            if child.is_dir() and (child / ".git").exists():
                repos.append(child)
    return repos

def get_recent_commits(repo_path, since="yesterday"):
    try:
        result = subprocess.run(
            ["git", "log", f"--since={since}", "--oneline", "--no-merges", "--author=", "--all"],
            cwd=repo_path, capture_output=True, text=True, timeout=5
        )
        lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
        return lines[:5]  # max 5 per repo
    except:
        return []

def notify(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": msg}).encode()
    urllib.request.urlopen(url, data)

def generate_standup():
    today = datetime.now().strftime("%A, %B %d")
    all_commits = []

    repos = get_git_repos()
    for repo in repos:
        commits = get_recent_commits(repo, since="24 hours ago")
        if commits:
            all_commits.append(f"📁 {repo.name}")
            for c in commits:
                # strip the hash prefix
                parts = c.split(" ", 1)
                msg = parts[1] if len(parts) > 1 else c
                all_commits.append(f"  • {msg}")

    lines = [f"📋 STANDUP — {today}\n"]
    lines.append("✅ YESTERDAY")
    if all_commits:
        lines.extend(all_commits)
    else:
        lines.append("  • No commits found (check manually)")

    lines.append("\n🎯 TODAY")
    lines.append("  • (Add your plans here)")

    lines.append("\n🚧 BLOCKERS")
    lines.append("  • None")

    msg = "\n".join(lines)
    print(msg)
    notify(msg)

if __name__ == "__main__":
    generate_standup()
