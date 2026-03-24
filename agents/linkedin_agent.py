#!/usr/bin/env python3
"""
LinkedIn Content Agent
Drafts a weekly LinkedIn post based on what Josh learned and shipped.
Sends draft to Telegram for review before posting.
"""
import os, json, subprocess, urllib.request, urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

BOT_TOKEN = "8696349618:AAFsqhznbNOWoRLXZ4ugzXOEzLmaRyi9geE"
CHAT_ID   = "8743898908"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

LEARNING_LOG = Path.home() / "agent-hq" / "data" / "learning_log.json"
WORKOUT_LOG  = Path.home() / "workout-agent" / "logs.json"

REPO_PATHS = [Path.home() / "code", Path.home() / "Documents", Path.home() / "Developer"]

def notify(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": msg}).encode()
    urllib.request.urlopen(url, data)

def get_recent_git_activity():
    commits = []
    for base in REPO_PATHS:
        if not base.exists(): continue
        for path in [base] + [c for c in base.iterdir() if c.is_dir() and (c/".git").exists()]:
            if not (path/".git").exists(): continue
            try:
                r = subprocess.run(
                    ["git","log","--since=7 days ago","--oneline","--no-merges"],
                    cwd=path, capture_output=True, text=True, timeout=5
                )
                for line in r.stdout.strip().split("\n"):
                    if line.strip():
                        parts = line.split(" ", 1)
                        if len(parts) > 1:
                            commits.append(f"{path.name}: {parts[1]}")
            except: pass
    return commits[:8]

def get_workout_wins():
    try:
        logs = json.loads(WORKOUT_LOG.read_text())
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        week_logs = [l for l in logs if l["date"] >= week_ago]
        total = sum(l["total_reps"] for l in week_logs)
        days = len(set(l["date"] for l in week_logs))
        return f"{total} push-ups across {days} days this week"
    except: return ""

def call_claude(prompt):
    if not ANTHROPIC_API_KEY:
        return "❌ Set ANTHROPIC_API_KEY in your environment to enable this agent."
    payload = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 1200,
        "messages": [{"role": "user", "content": prompt}]
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode(),
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
    )
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())["content"][0]["text"]

def draft_post():
    commits = get_recent_git_activity()
    wins    = get_workout_wins()
    week    = datetime.now().strftime("%B %d, %Y")

    commit_str = "\n".join(f"- {c}" for c in commits) if commits else "No recent commits found"
    prompt = f"""You are ghostwriting a LinkedIn post for Josh Menzies, a Platform Engineer at Nectar (CCaaS company).
He's 24, based in New York, focused on AI/ML engineering, AWS, Claude API, and building toward a Technical Co-Founder role.
His voice is: direct, confident, builder mindset, not corporate — like a sharp engineer who's thoughtful about career growth.

Week of: {week}

Recent code activity:
{commit_str}

Physical wins: {wins}

Write ONE compelling LinkedIn post (200-300 words) that:
- Opens with a hook (not "I'm excited to share")
- Shares a real insight, lesson, or observation from his work this week
- Ties to a broader trend in AI, platform engineering, or career growth
- Ends with a question or call to action to drive comments
- Feels authentic, not like a press release
- Uses 2-3 short paragraphs, maybe 1-2 bullet points max
- NO emojis spam, NO "thoughts?" at the end, NO generic filler

After the post, add on a new line:
---
💡 POSTING TIP: [one sentence on best time/hashtags to use]"""

    return call_claude(prompt)

def run():
    print("Drafting LinkedIn post...")
    post = draft_post()
    header = f"✍️ LINKEDIN DRAFT — Week of {datetime.now().strftime('%b %d')}\n\nReview and post if it looks good:\n\n"
    full_msg = header + post + "\n\n(Edit and post manually — or tell me to tweak it)"
    print(full_msg)
    notify(full_msg)

if __name__ == "__main__":
    run()
