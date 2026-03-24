#!/usr/bin/env python3
"""
Interview Prep Agent — daily AWS/AI/system design question via Telegram.
Rotates through a curated question bank. No API key needed.
Usage: interview_prep.py           (send today's question)
       interview_prep.py answer <your answer>  (log your answer)
       interview_prep.py random    (send a random question)
"""
import json, sys, random, urllib.request, urllib.parse
from datetime import datetime
from pathlib import Path

BASE     = Path.home() / "agent-hq"
LOG_FILE = BASE / "data" / "interview_prep.json"
BOT      = "8696349618:AAFsqhznbNOWoRLXZ4ugzXOEzLmaRyi9geE"
CHAT     = "8743898908"

QUESTIONS = [
    # AWS SAA
    {"q": "What is the difference between an S3 bucket policy and an IAM policy? When would you use each?", "cat": "AWS", "tag": "S3/IAM"},
    {"q": "Explain the difference between RDS Multi-AZ and Read Replicas. What problem does each solve?", "cat": "AWS", "tag": "RDS"},
    {"q": "A Lambda function is timing out at 15 minutes. What are your options?", "cat": "AWS", "tag": "Lambda"},
    {"q": "What is the difference between SQS Standard and FIFO queues? When does ordering matter?", "cat": "AWS", "tag": "SQS"},
    {"q": "Describe the shared responsibility model. Where does AWS end and your responsibility begin?", "cat": "AWS", "tag": "Security"},
    {"q": "You need to run a batch job once a day that takes 2 hours. What AWS service do you use and why?", "cat": "AWS", "tag": "Compute"},
    {"q": "What is the difference between NACLs and Security Groups in a VPC?", "cat": "AWS", "tag": "VPC"},
    {"q": "How does CloudFront improve performance and reduce costs for a global web application?", "cat": "AWS", "tag": "CloudFront"},
    {"q": "Explain how ECS Fargate differs from EC2-based ECS. What are the tradeoffs?", "cat": "AWS", "tag": "Containers"},
    {"q": "What is a NAT Gateway and when do you need one in a VPC?", "cat": "AWS", "tag": "VPC"},
    {"q": "Your EC2 instance needs to access S3 without hardcoded credentials. How do you do it?", "cat": "AWS", "tag": "IAM"},
    {"q": "Explain the difference between CloudWatch Metrics, Logs, and Alarms. How do they work together?", "cat": "AWS", "tag": "Monitoring"},
    {"q": "What is Route53 weighted routing and when would you use it?", "cat": "AWS", "tag": "DNS"},
    {"q": "A DynamoDB table is hot-partitioned. What causes this and how do you fix it?", "cat": "AWS", "tag": "DynamoDB"},
    {"q": "What is an ECS task definition? What does it contain?", "cat": "AWS", "tag": "Containers"},
    # System Design
    {"q": "Design a URL shortener like bit.ly. Walk through the data model, API, and scaling strategy.", "cat": "System Design", "tag": "Classic"},
    {"q": "Design a notification service that sends 10M push notifications per day reliably.", "cat": "System Design", "tag": "Scale"},
    {"q": "How would you design a distributed rate limiter?", "cat": "System Design", "tag": "Infra"},
    {"q": "Walk me through how you'd design a multi-tenant SaaS backend with per-customer isolation.", "cat": "System Design", "tag": "SaaS"},
    {"q": "How does a CDN work? What happens when a cache misses?", "cat": "System Design", "tag": "Networking"},
    {"q": "Design a job queue system that guarantees at-least-once delivery.", "cat": "System Design", "tag": "Reliability"},
    {"q": "What is eventual consistency? Give an example of where you'd accept it vs. where you wouldn't.", "cat": "System Design", "tag": "Databases"},
    {"q": "How would you migrate a monolith to microservices without downtime?", "cat": "System Design", "tag": "Architecture"},
    # AI / ML
    {"q": "What is RAG (Retrieval Augmented Generation) and when would you use it over fine-tuning?", "cat": "AI", "tag": "LLM"},
    {"q": "Explain vector embeddings. How are they used in semantic search?", "cat": "AI", "tag": "Embeddings"},
    {"q": "What is the difference between a prompt and a system prompt in a Claude/GPT API call?", "cat": "AI", "tag": "API"},
    {"q": "How would you evaluate whether an LLM-powered feature is working correctly in production?", "cat": "AI", "tag": "Eval"},
    {"q": "What is token context and why does it matter for LLM application design?", "cat": "AI", "tag": "LLM"},
    {"q": "Describe the difference between zero-shot, few-shot, and chain-of-thought prompting.", "cat": "AI", "tag": "Prompting"},
    {"q": "What is an MCP server? How does it extend what a Claude agent can do?", "cat": "AI", "tag": "AgentSDK"},
    {"q": "You're building an AI agent that needs to take actions and loop until a task is complete. What architecture do you use?", "cat": "AI", "tag": "Agents"},
    # Platform / DevOps
    {"q": "What is the difference between blue-green and canary deployments?", "cat": "DevOps", "tag": "Deployments"},
    {"q": "Explain how Terraform state works. What problems can arise in a team environment?", "cat": "DevOps", "tag": "IaC"},
    {"q": "What is a service mesh? Give an example of when you'd add one.", "cat": "DevOps", "tag": "Networking"},
    {"q": "How does Kubernetes handle pod scheduling? What is an affinity rule?", "cat": "DevOps", "tag": "K8s"},
    {"q": "Walk me through how you'd set up a CI/CD pipeline for a Python microservice on AWS.", "cat": "DevOps", "tag": "CI/CD"},
    {"q": "What is observability? How is it different from monitoring?", "cat": "DevOps", "tag": "Monitoring"},
    # Behavioral
    {"q": "Tell me about a time you had to learn a new technology quickly to deliver something. What did you do?", "cat": "Behavioral", "tag": "Learning"},
    {"q": "Describe a situation where you disagreed with a technical decision. What did you do?", "cat": "Behavioral", "tag": "Conflict"},
    {"q": "Tell me about the most impactful project you've worked on. How did you measure success?", "cat": "Behavioral", "tag": "Impact"},
    {"q": "How do you prioritize when you have multiple urgent tasks competing for your time?", "cat": "Behavioral", "tag": "Prioritization"},
    {"q": "Tell me about a time you introduced a new tool or process. How did you get buy-in?", "cat": "Behavioral", "tag": "Leadership"},
    {"q": "You're three days from a deadline and you discover a major technical blocker. What do you do?", "cat": "Behavioral", "tag": "Pressure"},
]

def load():
    try: return json.loads(LOG_FILE.read_text())
    except: return {"answered": [], "last_index": -1}

def save(data):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOG_FILE.write_text(json.dumps(data, indent=2))

def notify(msg):
    url  = f"https://api.telegram.org/bot{BOT}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": CHAT, "text": msg}).encode()
    try: urllib.request.urlopen(url, data, timeout=6)
    except: pass

def today_question():
    data  = load()
    # Rotate by day-of-year so same question shows all day
    idx   = datetime.now().timetuple().tm_yday % len(QUESTIONS)
    q     = QUESTIONS[idx]
    today = datetime.now().strftime("%Y-%m-%d")
    already_answered = any(a["date"] == today for a in data.get("answered", []))
    answered_tag = " [answered]" if already_answered else ""
    msg = (
        f"INTERVIEW PREP — {today}{answered_tag}\n"
        f"[{q['cat']} / {q['tag']}]\n\n"
        f"{q['q']}\n\n"
        f"Reply with your answer via: agents/interview_prep.py answer <your answer>"
    )
    print(msg)
    notify(msg)
    data["last_index"] = idx
    save(data)

def random_question():
    q   = random.choice(QUESTIONS)
    msg = (
        f"RANDOM PREP QUESTION\n"
        f"[{q['cat']} / {q['tag']}]\n\n"
        f"{q['q']}"
    )
    print(msg)
    notify(msg)

def log_answer(answer_text):
    data  = load()
    today = datetime.now().strftime("%Y-%m-%d")
    idx   = data.get("last_index", datetime.now().timetuple().tm_yday % len(QUESTIONS))
    q     = QUESTIONS[idx]
    data.setdefault("answered", []).append({
        "date": today,
        "question": q["q"],
        "category": q["cat"],
        "answer": answer_text,
    })
    save(data)
    print(f"Answer logged for: {q['tag']}")
    notify(f"Answer logged.\nQuestion: {q['q'][:80]}...\nYour answer: {answer_text[:200]}")

def stats():
    data = load()
    answered = data.get("answered", [])
    by_cat = {}
    for a in answered:
        by_cat[a["category"]] = by_cat.get(a["category"], 0) + 1
    print(f"Total answered: {len(answered)}")
    for cat, count in sorted(by_cat.items()):
        print(f"  {cat}: {count}")

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "today":
        today_question()
    elif args[0] == "random":
        random_question()
    elif args[0] == "answer" and len(args) >= 2:
        log_answer(" ".join(args[1:]))
    elif args[0] == "stats":
        stats()
    else:
        print("Usage: interview_prep.py [today|random|answer <text>|stats]")
