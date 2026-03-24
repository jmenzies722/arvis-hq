#!/usr/bin/env python3
"""
Daily Learning Agent — sends one focused AWS/AI/DevOps lesson at 9am.
Rotates through a curated lesson bank. Tracks progress, no repeats for 60 days.
"""
import json, hashlib, urllib.request, urllib.parse
from datetime import datetime
from pathlib import Path

BOT_TOKEN = "8696349618:AAFsqhznbNOWoRLXZ4ugzXOEzLmaRyi9geE"
CHAT_ID   = "8743898908"
BASE      = Path(__file__).parent.parent
PROGRESS  = BASE / "data" / "learning_progress.json"

LESSONS = [
    # AWS Core
    {"topic": "AWS IAM", "category": "AWS", "lesson": "IAM Roles vs Users vs Groups\n\nUsers = long-term credentials (avoid for services). Groups = collections of users, inherit policies. Roles = temporary credentials assumed by services, Lambda functions, EC2 instances, or cross-account access.\n\nKey principle: least privilege. Start with zero permissions, add only what's needed.\n\nPractice: Create a role for a Lambda function with only s3:GetObject on a specific bucket. That's it.\n\n💡 Interview angle: 'How do you secure cross-account access?' → IAM role with AssumeRole trust policy."},
    {"topic": "S3 Storage Classes", "category": "AWS", "lesson": "S3 Storage Tier Decision Tree\n\nStandard → active data, accessed frequently\nIntelligent-Tiering → unknown access patterns (auto-moves between tiers)\nStandard-IA → accessed < once/month, retrieval fee applies\nGlacier Instant → archived but need it in ms\nGlacier Flexible → hours retrieval, cheapest for compliance archives\nDeep Archive → 12hr retrieval, pennies per GB\n\n💡 Real world: Use Lifecycle Rules to auto-transition. S3 Standard → Standard-IA after 30 days → Glacier after 90. Set it and forget it."},
    {"topic": "VPC Fundamentals", "category": "AWS", "lesson": "VPC Mental Model\n\nVPC = your private data center in AWS. CIDR block = your IP space (e.g. 10.0.0.0/16 = 65,536 IPs).\n\nPublic subnet = has route to Internet Gateway. EC2 there gets a public IP.\nPrivate subnet = no direct internet. Uses NAT Gateway to call out (not receive).\n\nSecurity Groups = stateful firewall (allow inbound → return traffic auto-allowed).\nNACLs = stateless (must explicitly allow both directions). Applied at subnet level.\n\n💡 Pattern: Load balancer in public subnet → app servers in private → RDS in isolated subnet (no internet at all)."},
    {"topic": "Lambda Cold Starts", "category": "AWS", "lesson": "Lambda Cold Start Deep Dive\n\nCold start happens when: first invocation, after idle period, scaling out.\nTime breakdown: runtime init (200ms-2s) + code init (your /tmp, globals).\n\nMinimize it:\n• Provisioned Concurrency = pre-warmed instances (costs money)\n• Keep package size small (< 50MB unzipped)\n• Move heavy imports outside handler function\n• Use SnapStart for Java\n• Prefer Node.js or Python over Java/C# for cold start speed\n\n💡 If latency matters: SnapStart + Provisioned Concurrency on your critical path. For background jobs — don't care."},
    {"topic": "RDS vs Aurora", "category": "AWS", "lesson": "When to use RDS vs Aurora\n\nRDS: managed MySQL/Postgres/Oracle/SQL Server. You provision instance size. Familiar, predictable cost.\n\nAurora: AWS-optimized engine. 5x faster than MySQL, 3x Postgres. Shared distributed storage auto-grows. Read replicas in < 100ms lag. Aurora Serverless v2 scales down to 0.5 ACUs.\n\nChoose Aurora when:\n• You need read replicas\n• Traffic is spiky (Serverless)\n• You want global databases\n\nChoose RDS when:\n• You need specific Oracle/SQL Server\n• Cost predictability matters more than performance\n• Simple single-AZ app\n\n💡 Default answer in interviews: Aurora Postgres. It's what AWS wants you to use."},
    {"topic": "CloudWatch Alarms", "category": "AWS", "lesson": "CloudWatch Alarm States\n\nOK → metric within threshold\nALARM → metric breached threshold\nINSUFFICIENT_DATA → not enough data points yet (new metric, or gap)\n\nAnatomy of a good alarm:\n• Metric: CPUUtilization\n• Statistic: Average\n• Period: 300s (5 min)\n• Threshold: > 80%\n• Evaluation periods: 3 (alarm after 15min sustained)\n• TreatMissingData: breaching or notBreaching based on risk\n\n💡 Common pattern: Alarm → SNS topic → Lambda to auto-remediate OR PagerDuty/Slack webhook. Always set both OK and ALARM actions."},
    {"topic": "ECS vs EKS", "category": "AWS", "lesson": "ECS vs EKS Decision\n\nECS: AWS-native container orchestration. Simpler. Fargate = serverless (no EC2 to manage). Deep AWS integration (IAM task roles, ALB integration, CloudWatch).\n\nEKS: Managed Kubernetes. Industry standard. Portable (runs same YAML on GKE, AKS). More complex, more control. Need Helm, kube-proxy knowledge.\n\nChoose ECS + Fargate when:\n• Team is AWS-native, small\n• No need for Kubernetes portability\n• Want simplicity\n\nChoose EKS when:\n• Multi-cloud strategy\n• Team already knows K8s\n• Complex workloads (stateful apps, custom schedulers)\n\n💡 At a startup: ECS Fargate. At enterprise with existing K8s: EKS."},
    {"topic": "SQS vs SNS vs EventBridge", "category": "AWS", "lesson": "AWS Messaging Patterns\n\nSQS (Queue): One producer, one consumer. Message stays until consumed. Pull-based. Dead Letter Queue for failures. Best for: task queues, decoupling services.\n\nSNS (Pub/Sub): One message → many subscribers (email, SQS, Lambda, HTTP). Push-based. No retention. Best for: fan-out patterns, notifications.\n\nEventBridge: Event bus. Routes events by rules/patterns. Connects 200+ AWS services + SaaS. Best for: event-driven architectures, cross-service automation.\n\n💡 Pattern: Lambda writes to SNS → fans out to SQS queues for each team's processor. EventBridge for everything else event-driven."},
    # AI/ML
    {"topic": "RAG Architecture", "category": "AI", "lesson": "RAG (Retrieval-Augmented Generation)\n\nProblem: LLMs have a knowledge cutoff and can't know your private data.\nSolution: RAG = retrieve relevant docs → inject into prompt → LLM answers from that context.\n\nFlow:\n1. Ingest: chunk docs → embed → store in vector DB (Pinecone, pgvector, Chroma)\n2. Query: embed question → similarity search → retrieve top-K chunks\n3. Generate: prompt = question + retrieved chunks → LLM answer\n\nKey tuning levers:\n• Chunk size (too small = no context, too big = dilutes signal)\n• K (how many chunks to retrieve)\n• Embedding model (OpenAI ada-002, Cohere, local)\n\n💡 AWS native: Bedrock Knowledge Bases = managed RAG. Upload docs → it handles embedding + retrieval."},
    {"topic": "Prompt Engineering", "category": "AI", "lesson": "Prompt Engineering Fundamentals\n\nThe 5 elements of a strong prompt:\n1. Role: 'You are a senior DevOps engineer...'\n2. Context: what the user/system is, what data you have\n3. Task: specific, unambiguous instruction\n4. Format: 'Respond in JSON', 'Use bullet points', '3 sentences max'\n5. Constraints: 'Do not make up URLs', 'Only use provided context'\n\nTechniques:\n• Chain of Thought: 'Think step by step'\n• Few-shot: provide 2-3 examples before the question\n• Self-critique: 'Review your answer and fix any errors'\n\n💡 At Nectar / CCaaS: prompt templates for call summaries should include role (support agent context), format (structured JSON), and constraints (only summarize, don't interpret intent)."},
    {"topic": "Claude API Basics", "category": "AI", "lesson": "Claude API — Core Concepts\n\nMessages API format:\n  messages = [{role: 'user', content: 'Hello'}]\n  client.messages.create(model='claude-opus-4-6', max_tokens=1024, messages=messages)\n\nKey parameters:\n• max_tokens: hard cap on output length\n• temperature: 0 = deterministic, 1 = creative (default ~1)\n• system: sets persona/context, not in messages array\n• stop_sequences: tokens that halt generation\n\nTool use = structured function calling. Model decides when to call a tool, you execute it, return result.\n\n💡 Compliance API (your project): use system prompt to enforce constraints + tool use to validate actions before execution. Audit every call."},
    {"topic": "Vector Embeddings", "category": "AI", "lesson": "Vector Embeddings Explained\n\nEmbedding = converting text → array of numbers (e.g. 1536 floats) that capture semantic meaning.\n\nSimilar concepts → close vectors in space. Measured by cosine similarity or dot product.\n\nUse cases:\n• Semantic search (not keyword — meaning-based)\n• RAG retrieval\n• Duplicate detection\n• Clustering/classification\n\nModels:\n• OpenAI text-embedding-3-small (cheap, great)\n• Cohere embed-v3\n• AWS Bedrock Titan Embeddings\n• Local: sentence-transformers/all-MiniLM (no API cost)\n\n💡 For your Callbrief SaaS: embed call transcripts → find similar past calls → surface patterns. That's a premium feature."},
    {"topic": "LangGraph Basics", "category": "AI", "lesson": "LangGraph — Agent Workflows\n\nLangGraph = build multi-step AI agents as graphs. Each node = a step. Edges = conditions.\n\nKey concepts:\n• State: shared dict passed between nodes\n• Nodes: functions that read/modify state\n• Edges: unconditional (always go to X) or conditional (if state.y → go to X else Z)\n• Checkpointing: save state mid-graph for human-in-the-loop\n\nWhen to use:\n• Multi-step reasoning with branching\n• Agents that need to loop (retry, reflect, search again)\n• Human approval checkpoints\n\n💡 Arvis OS itself is a good LangGraph candidate — route incoming messages → classify intent → dispatch to right agent → collect result → reply."},
    # DevOps
    {"topic": "GitHub Actions CI/CD", "category": "DevOps", "lesson": "GitHub Actions — Mental Model\n\nWorkflow = YAML file in .github/workflows/. Triggered by push, PR, schedule, or manual.\n\nStructure:\n  on: [push]\n  jobs:\n    test:\n      runs-on: ubuntu-latest\n      steps:\n        - uses: actions/checkout@v4\n        - run: npm test\n\nKey patterns:\n• Secrets: ${{ secrets.AWS_ACCESS_KEY_ID }} — stored in repo settings\n• Environments: staging/production with manual approval gates\n• Matrix builds: test across Node 18, 20, 22 simultaneously\n• Caching: actions/cache for node_modules, pip, etc.\n\n💡 For Kiro rollout: build a workflow that runs on PR → lints + tests → deploys to staging → requires 1 approval → deploys to prod. That's a professional CI/CD pipeline."},
    {"topic": "Terraform Basics", "category": "DevOps", "lesson": "Terraform Core Concepts\n\nInfrastructure as Code: define AWS resources in .tf files, apply changes deterministically.\n\nWorkflow:\n  terraform init    → download providers\n  terraform plan    → see what will change (read-only)\n  terraform apply   → make the changes\n  terraform destroy → tear everything down\n\nKey concepts:\n• State file: tracks what Terraform manages. Store in S3 + DynamoDB lock for teams.\n• Resources: aws_instance, aws_s3_bucket, aws_iam_role\n• Variables: input via .tfvars or env (TF_VAR_name)\n• Outputs: expose values after apply (e.g. load balancer DNS)\n• Modules: reusable resource groups\n\n💡 At Nectar: Terraform for all AWS infra = reproducible, reviewable, auditable. No more clicking in console."},
    {"topic": "Docker Multi-Stage Builds", "category": "DevOps", "lesson": "Docker Multi-Stage Builds\n\nProblem: build tools (gcc, npm, test frameworks) bloat production images.\nSolution: multi-stage — use one image to build, copy only artifacts to final image.\n\nExample:\n  FROM node:20 AS builder\n  WORKDIR /app\n  COPY . .\n  RUN npm ci && npm run build\n\n  FROM node:20-alpine AS runtime\n  WORKDIR /app\n  COPY --from=builder /app/dist ./dist\n  COPY --from=builder /app/node_modules ./node_modules\n  CMD [\"node\", \"dist/index.js\"]\n\nResult: build image = 1.2GB, runtime image = 180MB.\n\n💡 Alpine base images add ~5MB. Node Alpine = 50x smaller than Ubuntu. Always use alpine for production."},
    {"topic": "Observability — Logs Metrics Traces", "category": "DevOps", "lesson": "The Observability Triangle\n\nLogs = what happened (events, errors, request details). High volume, structured (JSON). Use: debug specific incidents.\n\nMetrics = how much/fast/often (numbers over time). Low volume, cheap to store. Use: dashboards, alerts, trends.\n\nTraces = how a request flowed through distributed systems. Request ID that follows a call across 10 microservices.\n\nAWS stack:\n• Logs → CloudWatch Logs (+ Insights for queries)\n• Metrics → CloudWatch Metrics + custom metrics via PutMetricData\n• Traces → X-Ray (instrument Lambda, ECS, API Gateway)\n\n💡 Rule of thumb: alert on metrics, debug with logs, trace across services. Add request IDs to every log line."},
    {"topic": "API Gateway + Lambda Pattern", "category": "AWS", "lesson": "Serverless API Pattern\n\nAPI Gateway → Lambda = the standard AWS serverless API.\n\nSetup:\nREST API Gateway → ANY method → Lambda proxy integration\nLambda receives: event.path, event.method, event.body, event.headers\nLambda returns: {statusCode, headers, body: JSON.stringify(data)}\n\nHTTP API (new) vs REST API:\n• HTTP API = cheaper, faster, simpler. Use for most APIs.\n• REST API = more features (WAF, usage plans, request validation, caching). Use for public APIs.\n\n💡 For Callbrief SaaS: HTTP API Gateway → Lambda → process transcript → return summary. Add API key authentication via usage plan. That's a billable product."},
    {"topic": "AWS Cost Optimization", "category": "AWS", "lesson": "AWS Cost Levers (in order of impact)\n\n1. Right-size instances: use Compute Optimizer recommendations. t3.xlarge → t3.large often saves 40%.\n2. Reserved Instances / Savings Plans: 1-year commitment = 40% off. 3-year = 60%.\n3. Spot Instances: up to 90% off for interruptible workloads (batch, CI runners).\n4. S3 Lifecycle Rules: auto-move to cheaper tiers (Standard → IA → Glacier).\n5. Delete idle resources: unattached EBS volumes, unused Elastic IPs, old snapshots.\n6. Turn off non-prod: Lambda on schedule to stop dev EC2 at 7pm, restart at 8am.\n\n💡 Quick win: run Cost Explorer → sort by service → find your top 3 spenders → address each. Most accounts waste 20-30% on forgotten resources."},
    {"topic": "Security Groups Deep Dive", "category": "AWS", "lesson": "Security Groups — Common Patterns\n\nSecurity groups are stateful virtual firewalls. Attached to ENIs (not subnets).\n\nKey rules:\n• By default: all outbound allowed, all inbound denied\n• Reference other security groups (not just IPs) — scales better\n• No deny rules — it's allowlist only\n\nProduction pattern:\n  alb-sg: inbound 443 from 0.0.0.0/0\n  app-sg: inbound 3000 from alb-sg only\n  db-sg:  inbound 5432 from app-sg only\n\nNever: inbound 22 from 0.0.0.0/0. Use Systems Manager Session Manager instead (no port 22 needed at all).\n\n💡 Interview answer to 'how do you secure an EC2 instance': SSM Session Manager + no public IP + private subnet + security group referencing."},
    {"topic": "Bedrock vs SageMaker", "category": "AWS", "lesson": "AWS AI Services — When to Use What\n\nBedrock:\n• Call foundation models via API (Claude, Llama, Titan, Mistral)\n• No training, no infrastructure\n• Managed RAG (Knowledge Bases), agents, guardrails\n• Use when: you want AI features without ML expertise\n\nSageMaker:\n• Full ML platform: train, tune, deploy your own models\n• SageMaker Endpoints = your model behind an API\n• Expensive and complex\n• Use when: you have proprietary data + need custom model\n\nRekognition, Comprehend, Transcribe, Textract = purpose-built AI APIs for specific tasks (vision, NLP, speech, OCR).\n\n💡 For Callbrief and Claude Enterprise: Bedrock + Claude is your stack. Zero infra, production-grade, SOC2 compliant."},
]

def load_progress():
    if PROGRESS.exists():
        return json.loads(PROGRESS.read_text())
    return {"sent": [], "last_index": -1}

def save_progress(p):
    PROGRESS.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS.write_text(json.dumps(p, indent=2))

def get_todays_lesson(p):
    """Pick next lesson not sent in last 60 days."""
    sent_recent = set(p["sent"][-60:]) if p["sent"] else set()
    for i, lesson in enumerate(LESSONS):
        key = hashlib.md5(lesson["topic"].encode()).hexdigest()[:8]
        if key not in sent_recent:
            return i, lesson, key
    # All done — reset
    p["sent"] = []
    return 0, LESSONS[0], hashlib.md5(LESSONS[0]["topic"].encode()).hexdigest()[:8]

def tg(text):
    url  = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": text}).encode()
    urllib.request.urlopen(urllib.request.Request(url, data), timeout=10)

def broadcast_to_hq(message, msg_type="outgoing"):
    try:
        import json as _json
        url  = "http://localhost:8766/api/log/telegram"
        data = _json.dumps({"message": message[:300], "type": msg_type}).encode()
        req  = urllib.request.Request(url, data, {"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=3)
    except Exception:
        pass

def main():
    p     = load_progress()
    idx, lesson, key = get_todays_lesson(p)
    total = len(LESSONS)
    done  = len(set(p["sent"]))

    msg = (
        f"📚 Daily Learning — {lesson['category']}\n"
        f"{'─'*28}\n"
        f"Topic: {lesson['topic']}\n\n"
        f"{lesson['lesson']}\n\n"
        f"Progress: {done}/{total} topics covered"
    )

    tg(msg)
    print(msg)
    broadcast_to_hq(f"Daily Learning: {lesson['topic']} ({lesson['category']})", "outgoing")

    p["sent"].append(key)
    p["last_index"] = idx
    save_progress(p)

    # Log
    try:
        log_file = BASE / "data" / "activity_log.json"
        data     = json.loads(log_file.read_text()) if log_file.exists() else []
        next_id  = (max(r.get("id", 0) for r in data) + 1) if data else 1
        data.append({"id": next_id, "timestamp": datetime.now().isoformat(), "date": datetime.now().strftime("%Y-%m-%d"), "time": datetime.now().strftime("%H:%M:%S"), "agent_id": "daily_learning", "agent_name": "Daily Learning", "category": "work", "status": "success", "summary": f"Lesson: {lesson['topic']}", "duration_ms": 0})
        log_file.write_text(json.dumps(data, indent=2))
    except: pass

if __name__ == "__main__":
    main()
