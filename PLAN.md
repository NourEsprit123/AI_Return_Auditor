# 🤖 AI Return Auditor — Project Plan & AI Techniques

> **Visual E-Commerce Return & Refund Auditor**
> Advanced Deep Learning Exam Project

---

## 📋 Current Project Status

| Component | Status | Notes |
|-----------|--------|-------|
| Agent 1 — Vision Agent | ✅ Complete | Full ReAct loop, Gemini multimodal, Pydantic output |
| Agent 2 — RAG Agent | ❌ To Build | `rag_agent.py`, `documents.py`, `embeddings.py`, `retriever.py` all empty |
| Agent 3 — Decision Agent | ❌ To Build | `decision_agent.py` is blank |
| Policy Knowledge Base | ❌ Empty | 3 `.txt` files exist but all empty |
| Orders Data (CSV) | ❌ Empty | `orders.csv` is blank |
| Decision View (Streamlit) | ⚠️ Hardcoded | Shows fake 89% / APPROVED — not connected to real agents |
| AI Analysis View (Streamlit) | ✅ Works | Connected to Vision Agent correctly |
| Full Streamlit UI | ✅ Complete | All 5 pages working |
| FastAPI Layer (for n8n) | ❌ To Build | Needed so n8n can call Python agents via HTTP |
| n8n Workflow | ❌ To Build | `workflow.json` is empty |

---

## 🏗️ System Architecture

### Multi-Agent Pipeline

```
Customer Return Request
 (image + description + order info)
           │
           ▼
┌──────────────────────────┐
│  Agent 1 — Vision Agent  │  ← Multimodal AI (Gemini)
│  Product damage analysis │
└─────────────┬────────────┘
              │  VisionAnalysis (structured JSON)
              ▼
┌──────────────────────────┐
│  Agent 2 — RAG Agent     │  ← ChromaDB + sentence-transformers
│  Policy retrieval        │
└─────────────┬────────────┘
              │  PolicyResult (Top-3 chunks + sources)
              ▼
┌──────────────────────────┐
│  Agent 3 — Decision      │  ← Gemini + Python guardrails
│  Claim evaluation        │
└─────────────┬────────────┘
              │
      ┌───────┴────────┐
      ▼                ▼
 ✅ APPROVED     ⚠️ HUMAN REVIEW
```

### n8n Automation Layer

```
Streamlit ──HTTP POST──► n8n Webhook
                               │
               ┌───────────────┼───────────────┐
               ▼               ▼               ▼
         POST /vision     POST /rag      POST /decision
          (FastAPI)        (FastAPI)      (FastAPI)
               └───────────────┼───────────────┘
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
               APPROVED             HUMAN_REVIEW
                    │                     │
              Log to sheet         Email alert to
                                   human reviewer
```

---

## 🧠 AI Techniques — Per Agent

---

### Agent 1 — Vision Agent ✅

#### Technique 1: Multimodality

**What it is:**
The model receives **two different input types simultaneously**:
- 🖼️ An **image** — the product photo submitted by the customer
- 📝 **Text** — the customer's written description

```python
# Gemini receives both modalities in the same API call
response = client.models.generate_content(
    model="gemini-2.0-flash-lite",
    contents=[user_prompt, image],   # ← text + PIL image together
    config={
        "response_mime_type": "application/json",
        "response_schema": VisionAnalysis,
    }
)
```

**Why Gemini Flash?**
Gemini is **natively multimodal** — it was trained on text and image pairs from the start, not as an add-on. This enables cross-modal reasoning: comparing what it *sees* in the image with what the customer *claims* in text.

---

#### Technique 2: Prompt Engineering

| Technique | Where | What it does |
|-----------|-------|--------------|
| **Role prompting** | `prompts/vision_agent_v1.txt` | "You are the Multimodal Product Damage Analyzer..." — defines identity and scope |
| **Constraint prompting** | `prompts/vision_agent_v1.txt` | "You must NOT approve, reject, decide..." — prevents overstepping |
| **Output formatting** | `prompts/vision_agent_v1.txt` | "Return only the requested structured information" |
| **Iterative prompting** | `agents/vision_agent.py` loop | Each re-attempt injects the previous reasoning as context |
| **Task-specific prompting** | `_analyze_image()` method | Different instructions per step: `VERIFY_DAMAGE`, `VERIFY_PRODUCT_IDENTITY`, etc. |
| **Prompt versioning** | `prompts/` directory | `vision_agent_v1.txt` — versioned for experimentation |

**Why not fine-tuning?**
Fine-tuning requires thousands of labeled `{image, description, correct_output}` examples + GPU compute + regular retraining. Prompt engineering achieves the same with zero training data and instant updates (just edit the `.txt` file).

---

#### Technique 3: Structured Output (Pydantic)

Instead of raw LLM text, the agent forces a validated, typed Python object:

```python
class VisionAnalysis(BaseModel):
    product_category: str
    product_type: str
    damage_type: str
    damage_location: str
    severity: str        # Low | Medium | High | None | Unknown
    confidence: float    # validated: 0.0 <= x <= 1.0
    visual_evidence: str
    description_consistency: str
    uncertainty: str
```

Pydantic validates types and constraints at runtime — downstream agents receive reliable data every time.

---

#### Technique 4: Agentic ReAct Loop

The agent runs a **multi-step reasoning loop** (inspired by the ReAct pattern: Reasoning + Acting):

```
OBSERVE  → Call Gemini with image + description
REASON   → Evaluate confidence, consistency, uncertainty
PLAN     → Decide what to verify next
ACT      → Run targeted re-analysis
(repeat up to MAX_ATTEMPTS = 3)
```

| Action | Trigger |
|--------|---------|
| `ACCEPT` | confidence ≥ 0.80, consistent, no uncertainty |
| `VERIFY_PRODUCT_IDENTITY` | description doesn't match visible product |
| `VERIFY_DAMAGE` | damage details unclear |
| `VERIFY_DESCRIPTION_CONSISTENCY` | inconsistency detected |
| `ESCALATE` | max attempts reached or unresolvable contradiction |

---

### Agent 2 — RAG Agent ❌ (To Build)

#### Technique: Retrieval-Augmented Generation (RAG)

**What it solves:** The LLM does not know your company's specific return policies. Instead of hallucinating generic rules, the system retrieves the actual relevant policy at runtime.

**Full RAG pipeline:**

```
Policy .txt files
       │
       ▼
Document Loading         ← rag/documents.py
       │
       ▼
Text Chunking            ← 500 chars, 100 overlap
       │
       ▼
Embedding Model          ← all-MiniLM-L6-v2 (384 dimensions)
       │
       ▼
Vector Store             ← ChromaDB (local, persistent)
       │       ← at query time
       ▼
Query (damage_type + product_type + severity)
       │
       ▼
Cosine Similarity Search
       │
       ▼
Top-3 Policy Chunks  →  PolicyResult  →  Agent 3
```

---

#### Chunking Strategy

| Parameter | Choice | Why |
|-----------|--------|-----|
| Chunk size | 500 characters | Policy rules are short paragraphs; too large = noise |
| Overlap | 100 characters | Prevents a rule from being split across chunks |
| Split strategy | Paragraph / sentence boundary | Keeps logical rule units intact |

This is called **fixed-size chunking with overlap** — the standard RAG baseline.

---

#### Embedding Model

| Model | Dimensions | Cost | Why |
|-------|-----------|------|-----|
| `all-MiniLM-L6-v2` ✅ chosen | 384 | Free, offline | Already installed, no internet needed |
| `text-embedding-3-small` | 1536 | Paid per call | Better quality but requires OpenAI API key |

**What embeddings do:** Convert text into a dense vector where **semantically similar texts produce similar vectors**. This enables meaning-based search instead of keyword matching.

---

#### Vector Database — ChromaDB

- Runs **locally** — no server, no internet, no cost
- Already in `requirements.txt`
- Persistent — embeddings computed once, reused on every run
- Simple Python API compatible with `sentence-transformers`

---

#### Cosine Similarity

At query time the agent embeds the query and finds the closest policy chunks by **cosine similarity** — measures the angle between vectors (semantic direction), not their magnitude. Robust for comparing text of different lengths.

---

### Agent 3 — Decision Agent ❌ (To Build)

#### Technique 1: Few-Shot + Chain-of-Thought Prompt Engineering

```
System role:
  "You are the Claim Evaluator of an e-commerce return system."

Few-shot examples:
  Example 1: [damaged product, consistent, policy applies] → APPROVED
  Example 2: [no visible damage, description inconsistent] → HUMAN_REVIEW

Chain-of-thought instruction:
  Step 1: Review visual evidence from Agent 1
  Step 2: Check relevant policies retrieved by Agent 2
  Step 3: Verify order eligibility (delivery date, return window)
  Step 4: Apply guardrail conditions
  Step 5: Produce a justified, structured decision

Output: DecisionResult (typed, validated)
```

---

#### Technique 2: Guardrails (Rule-Based Safety Layer)

**Before** calling Gemini, deterministic Python rules block automatic approval in unsafe cases:

```python
# Pure Python — no AI involved
if vision_result.confidence < 0.60:
    return DecisionResult(decision="HUMAN_REVIEW",
                          reason="Low vision confidence")

if "inconsistent" in vision_result.description_consistency.lower():
    return DecisionResult(decision="HUMAN_REVIEW",
                          reason="Visual evidence does not match description")

if not policy_result.chunks:
    return DecisionResult(decision="HUMAN_REVIEW",
                          reason="No applicable policy found")

if order_days_since_delivery > return_window_days:
    return DecisionResult(decision="HUMAN_REVIEW",
                          reason="Return window has expired")
```

**Why this matters:** Guardrails make the system **safe and explainable** — no uncertain case is ever automatically approved. This is a core principle of responsible AI.

---

#### Technique 3: Multi-Agent Synthesis

Agent 3 does not re-analyze the image or re-read the policies. It **synthesizes** the outputs of Agents 1 and 2:

```python
def decide(
    vision_result: VisionAnalysis,    # structured output from Agent 1
    policy_result: PolicyResult,       # Top-3 chunks from Agent 2
    order_info: dict                   # from data/orders.csv
) -> DecisionResult:
    ...
```

This is the core principle of **multi-agent systems**: each agent has one responsibility, and agents communicate through structured typed interfaces.

---

## 📊 Full Techniques Summary

| Agent | Technique | Why this choice |
|-------|-----------|-----------------|
| Agent 1 | **Multimodality** | Damage requires seeing the image AND reading the description |
| Agent 1 | **Prompt Engineering** (Role + Constraint + Iterative) | No labeled dataset for fine-tuning |
| Agent 1 | **Structured Output** (Pydantic) | Downstream agents need reliable typed data |
| Agent 1 | **ReAct Agentic Loop** | Single-shot analysis insufficient; multi-step verification needed |
| Agent 2 | **RAG** | Ground decisions in real company policy, not hallucination |
| Agent 2 | **Fixed-Size Chunking** (500/100) | Policy rules are short; overlap prevents rule splitting |
| Agent 2 | **Sentence Embeddings** (all-MiniLM-L6-v2) | Free, offline, already installed |
| Agent 2 | **Cosine Similarity + ChromaDB** | Local, free, persistent; cosine captures semantic direction |
| Agent 3 | **Few-Shot + Chain-of-Thought** | Model needs examples and step-by-step reasoning |
| Agent 3 | **Guardrails** (Python rules) | Prevent unsafe auto-approvals for uncertain cases |
| Agent 3 | **Multi-Agent Synthesis** | Separation of concerns; one responsibility per agent |
| All | **No fine-tuning** | No labeled dataset; prompt engineering is sufficient |

---

## 🔄 n8n Integration

### Role of n8n

n8n is the **workflow orchestration and automation layer** — it is **not** an AI agent.

| Layer | Technology | Role |
|-------|-----------|------|
| AI Agents | Python + Gemini | Vision, RAG, Decision logic |
| Interface | Streamlit | User-facing web application |
| Automation | n8n | Connects components, notifications, logging |
| API Bridge | FastAPI | Exposes Python agents as HTTP endpoints |

### n8n Workflow Steps

1. **Webhook Trigger** — receives JSON claim payload from Streamlit
2. **HTTP Request** → `POST /analyze/vision` — calls Vision Agent
3. **HTTP Request** → `POST /analyze/rag` — calls RAG Agent
4. **HTTP Request** → `POST /analyze/decision` — calls Decision Agent
5. **IF node** — branches on `APPROVED` vs `HUMAN_REVIEW`
6. **Email / Notification** — alerts human reviewer if escalated
7. **Google Sheets / Log** — records every decision for audit trail

---

## 🗺️ Implementation Roadmap

| Step | Task | File | Status |
|------|------|------|--------|
| 1 | Fill policy knowledge base | `data/knowledge_base/*.txt` | ❌ Empty |
| 2 | Fill orders sample data | `data/orders.csv` | ❌ Empty |
| 3 | Build document loader + chunker | `rag/documents.py` | ❌ Empty |
| 4 | Build embeddings wrapper | `rag/embeddings.py` | ❌ Empty |
| 5 | Build ChromaDB store + search | `rag/retriever.py` | ❌ Empty |
| 6 | Build RAG Agent | `agents/rag_agent.py` | ❌ Empty |
| 7 | Build Decision Agent | `agents/decision_agent.py` | ❌ Empty |
| 8 | Build FastAPI server | `services/api.py` | ❌ To create |
| 9 | Build n8n workflow | `n8n/workflow.json` | ❌ Empty |
| 10 | Connect Decision view to real agents | `views/decision.py` | ⚠️ Hardcoded |

---

## 🧰 Technology Stack

| Category | Technology |
|----------|-----------|
| Language | Python 3.11+ |
| Interface | Streamlit |
| AI / LLM | Google Gemini API (`gemini-2.0-flash-lite`) |
| Multimodal AI | Gemini (natively multimodal — text + image) |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`, 384 dimensions) |
| Vector Database | ChromaDB (local, persistent, no server) |
| Data Validation | Pydantic |
| Image Processing | Pillow (PIL) |
| Automation | n8n |
| API Layer | FastAPI |
| Configuration | python-dotenv |

---

*Project: AI Return Auditor — Advanced Deep Learning Exam*
