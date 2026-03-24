#!/usr/bin/env python3
"""
Meeting Prep Agent
Usage: python3 meeting_prep.py "Q2 Review with Michael" "strategy, budget, Kiro rollout"
Sends a structured prep brief to Telegram.
"""
import sys, subprocess, urllib.request, urllib.parse, os, json
from datetime import datetime

BOT_TOKEN = "8696349618:AAFsqhznbNOWoRLXZ4ugzXOEzLmaRyi9geE"
CHAT_ID   = "8743898908"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

def notify(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": msg}).encode()
    urllib.request.urlopen(url, data)

def call_claude(prompt):
    if not ANTHROPIC_API_KEY:
        return "❌ ANTHROPIC_API_KEY not set. Add it to ~/.zshrc as ANTHROPIC_API_KEY=sk-..."
    import urllib.request, json
    payload = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 1024,
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

def generate_prep(meeting_title, context=""):
    now = datetime.now().strftime("%A, %B %d at %I:%M %p")
    prompt = f"""You are a sharp executive assistant preparing Josh Menzies (Platform Engineer at Nectar, a CCaaS company) for an upcoming meeting.

Meeting: {meeting_title}
Context: {context if context else "No additional context provided"}
Current time: {now}

Generate a tight meeting prep brief in this exact format (plain text, no markdown):

📋 MEETING PREP — {meeting_title}

🎯 OBJECTIVE
[1-2 sentences: what this meeting is probably trying to accomplish]

👥 ATTENDEES
[List likely attendees based on meeting title, with one-line context on each]

📌 KEY TALKING POINTS
[3-5 specific points Josh should be ready to discuss]

❓ SMART QUESTIONS TO ASK
[2-3 questions that demonstrate strategic thinking]

⚠️ WATCH OUT FOR
[1-2 potential friction points or things to be prepared for]

✅ BRING / PREP
[Specific things to have ready: data, slides, updates, etc.]

Keep it under 300 words. Be specific, not generic."""

    return call_claude(prompt)

if __name__ == "__main__":
    title   = sys.argv[1] if len(sys.argv) > 1 else "Meeting"
    context = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
    print(f"Prepping for: {title}...")
    brief = generate_prep(title, context)
    print(brief)
    notify(brief)
