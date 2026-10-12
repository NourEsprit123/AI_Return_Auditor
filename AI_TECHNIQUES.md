# 🎓 AI Techniques — Where to Use & Which Type to Choose

> Companion guide for the **AI Return Auditor** project
> Covers: Prompt Engineering · Fine-Tuning · RAG

---

## 1. 🛠️ Prompt Engineering

### What is it?
Prompt Engineering is the practice of **carefully designing the text instructions
you give to an LLM** to control its behavior, output format, and reasoning style —
without changing the model weights.

---

### Where to use it in this project

| Agent | Where exactly | Why |
|-------|--------------|-----|
| **Agent 1 — Vision** | `prompts/vision_agent_v1.txt` | Define role, scope, forbidden actions, output format |
| **Agent 1 — Vision** | `agents/vision_agent.py` `_analyze_image()` | Different instruction per attempt (iterative prompting) |
| **Agent 3 — Decision** | Inside `agents/decision_agent.py` | Guide the model to reason step by step before deciding |

---

### Types of Prompt Engineering used (and why)

#### 1.1 Role Prompting
Tell the model who it is and what its boundaries are.

```
You are the Multimodal Product Damage Analyzer
of an e-commerce return verification system.
Your role is ONLY to analyze the visual evidence.
```

**Why here:** Without a clear role, Gemini might start making decisions
(approve/reject) instead of just analyzing the damage.
Role prompting constrains the scope of the model.

---

#### 1.2 Constraint Prompting
Explicitly list what the model must NOT do.

```
You must NOT:
- approve the return
- reject the return
- decide refund eligibility
- invent information that cannot be observed
```

**Why here:** LLMs tend to be "helpful" and try to give a final answer.
Constraint prompting forces Agent 1 to stay in its lane —
evidence collection only, not decision making.

---

#### 1.3 Output Format Prompting
Tell the model exactly what structure to return.

```
Return only the requested structured VisionAnalysis result.
```

Combined with Pydantic `response_schema`, this guarantees
a valid JSON object every time.

**Why here:** Downstream agents (RAG, Decision) consume the output directly.
Unstructured text would break the pipeline.

---

#### 1.4 Iterative / Chain-of-Thought Prompting
Each re-attempt of the Vision Agent injects the previous reasoning
as context, building a reasoning chain:

```
Previous agent reasoning:
The visible product is eyeglasses, but the customer described shoes.
The agent must verify the product identity independently.
```

**Why here:** The ReAct loop needs continuity between steps.
Injecting previous reasoning prevents the model from
"forgetting" what was already found.

---

#### 1.5 Task-Specific Prompting
Different instructions depending on what needs to be verified:

| Instruction | Trigger |
|-------------|---------|
| `Perform the initial visual analysis` | Attempt 1 |
| `This is a targeted product identity verification` | After inconsistency detected |
| `This is a targeted damage verification` | After unclear damage |
| `This is the final verification attempt` | Last attempt |

**Why here:** Generic instructions produce generic results.
Targeted instructions per step produce precise, focused outputs.

---

#### 1.6 Few-Shot Prompting (Agent 3 only)
Provide 2–3 worked examples of correct decisions inside the prompt:

```
Example 1:
  Vision: broken hinge, eyeglasses, high severity, consistent
  Policy: "Products with manufacturing defects are eligible for return within 30 days"
  Order: delivered 5 days ago
  → Decision: APPROVED — Visible defect confirmed, policy applies, within window

Example 2:
  Vision: no visible damage, description inconsistent
  Policy: "Return requires visible evidence of damage"
  Order: delivered 20 days ago
  → Decision: HUMAN_REVIEW — No visual evidence supports the claim
```

**Why here:** Agent 3 makes high-stakes decisions.
Few-shot examples show the model the exact reasoning format expected,
reducing hallucination and improving consistency.

---

#### 1.7 Prompt Versioning
Prompts are stored in separate `.txt` files:

```
prompts/
└── vision_agent_v1.txt   ← current version
└── vision_agent_v2.txt   ← future improved version
```

**Why:** Versioning allows you to compare prompt performance
across test cases without modifying code.
This is standard practice in LLM-based systems.

---

### When NOT to use Prompt Engineering
- When you have thousands of labeled examples → use Fine-Tuning instead
- When the task requires memorizing large volumes of domain data → use RAG instead

---

## 2. 🎯 Fine-Tuning

### What is it?
Fine-tuning means **retraining an existing pre-trained model on your specific dataset**
to adapt its weights for your task.
The model "learns" from your examples and integrates them permanently.

---

### Where it could apply in this project (theoretically)

| Agent | What you would fine-tune | What you would need |
|-------|--------------------------|---------------------|
| **Agent 1 — Vision** | A vision model to classify damage types | Thousands of {image → damage_type, severity} labeled pairs |
| **Agent 3 — Decision** | A text model to classify return decisions | Thousands of {vision_result + policy + order → APPROVED/HUMAN_REVIEW} labeled pairs |

---

### Why we do NOT use fine-tuning in this project

| Reason | Explanation |
|--------|-------------|
| **No dataset** | We have zero labeled {image, correct_output} examples |
| **Cost** | Fine-tuning Gemini or similar models requires GPU compute and API credits |
| **Maintenance** | Every time policies change, the model must be retrained |
| **Prompt engineering is sufficient** | For this academic project scope, prompt engineering achieves the required performance |
| **Overkill** | Fine-tuning is justified at production scale with millions of claims, not for a university project |

---

### When you WOULD use fine-tuning (future / production)

```
Scenario: You have 50,000 past return claims with verified decisions.
Solution: Fine-tune a classification head on top of a vision encoder
          to directly predict damage_type + severity from image.

Result:   Faster inference, lower API cost, higher accuracy on your
          specific product catalog.
```

---

### Types of Fine-Tuning (for academic knowledge)

| Type | What it does | When to use |
|------|-------------|-------------|
| **Full fine-tuning** | Update all model weights | Large dataset, maximum performance |
| **LoRA (Low-Rank Adaptation)** | Update only small adapter layers | Limited GPU memory, efficient |
| **QLoRA** | LoRA + quantization (4-bit) | Very limited resources |
| **Instruction fine-tuning** | Teach model to follow instruction format | When base model ignores your prompt structure |
| **RLHF** | Reward model + reinforcement learning | When you want human preference alignment |

**For this project:** If fine-tuning were required,
**LoRA** would be the recommended choice — efficient, low GPU cost,
and works well for adapting instruction-following behavior.

---

## 3. 📚 RAG — Retrieval-Augmented Generation

### What is it?
RAG means **giving the LLM access to external knowledge at query time**
by retrieving relevant documents from a knowledge base
and injecting them into the prompt as context.

The model does not memorize the knowledge — it reads it fresh each time.

---

### Where to use it in this project

| Agent | Where exactly | What is retrieved |
|-------|--------------|-------------------|
| **Agent 2 — RAG Agent** | `agents/rag_agent.py` | Return policy, refund conditions, warranty rules |
| **Agent 3 — Decision** | Receives RAG output as input | Cited policy chunks justify the decision |

---

### Why RAG here instead of just prompting the policy?

| Option | Problem |
|--------|---------|
| Put full policy in the prompt | Policy can be very long — exceeds context window, adds noise |
| Let model use its training data | Model was not trained on YOUR specific company policy |
| RAG | Retrieves only the 3 most relevant chunks — precise, grounded, scalable |

---

### Types of RAG (and which we use)

#### 3.1 Naive RAG (basic pipeline) ✅ Used here

```
Query → Embed → Search → Retrieve Top-K → Inject into prompt → LLM
```

Simple, fast, sufficient for policy documents.

**Why chosen:** Our knowledge base is small (3 policy files).
Naive RAG is perfectly adequate and easy to explain.

---

#### 3.2 Advanced RAG (for academic knowledge)

| Technique | What it adds | When useful |
|-----------|-------------|-------------|
| **Hybrid Search** | Combines dense (vector) + sparse (BM25 keyword) search | When exact keywords matter (e.g. "30 days") |
| **Reranking** | Re-scores retrieved chunks with a cross-encoder | When top-K order matters for quality |
| **HyDE** | Generates a hypothetical answer, embeds that to search | When queries are too short or vague |
| **Self-querying** | LLM generates the search query from user input | When user input is informal or ambiguous |
| **Recursive retrieval** | Retrieves summaries first, then details | For very large document collections |

**For this project:** Naive RAG is justified.
If the knowledge base grew to hundreds of documents,
adding **Hybrid Search + Reranking** would be the next step.

---

### Chunking Strategy — Which type and why

| Type | What it does | Best for |
|------|-------------|----------|
| **Fixed-size with overlap** ✅ Used | Split every N chars, overlap M chars | Short policy paragraphs — our case |
| **Sentence-based** | Split at sentence boundaries | Narrative documents |
| **Recursive** | Split by paragraph → sentence → word | Mixed-format documents |
| **Semantic** | Split where meaning changes (embeddings) | Long complex documents |

**Chosen:** Fixed-size (500 chars, 100 overlap)
**Why:** Policy documents are short, structured paragraphs.
Fixed-size chunking keeps each rule intact.
The 100-char overlap prevents a rule from being cut in half.

---

### Embedding Model — Which type and why

| Model | Type | Dimensions | Cost | Quality |
|-------|------|-----------|------|---------|
| `all-MiniLM-L6-v2` ✅ Used | Bi-encoder | 384 | Free, offline | Good for short texts |
| `all-mpnet-base-v2` | Bi-encoder | 768 | Free, offline | Better, slower |
| `text-embedding-3-small` | OpenAI API | 1536 | Paid | High quality |
| `text-embedding-3-large` | OpenAI API | 3072 | Expensive | Highest quality |

**Chosen:** `all-MiniLM-L6-v2`
**Why:** Already installed via `sentence-transformers`, works offline,
no API key needed, 384 dimensions is more than sufficient for
short policy paragraphs.

---

### Retrieval Method — Which type and why

| Method | How it works | Best for |
|--------|-------------|----------|
| **Dense retrieval (cosine)** ✅ Used | Compare embedding vectors by angle | Semantic meaning search |
| **Sparse retrieval (BM25)** | Keyword frequency scoring (TF-IDF) | Exact keyword match |
| **Hybrid** | Combines both with RRF scoring | Best of both worlds |

**Chosen:** Dense retrieval with cosine similarity via ChromaDB
**Why:** Semantic search finds "product received damaged" even if
the policy says "items with visible defects" — keyword search would miss this.

---

### Vector Database — Which type and why

| Database | Type | Cost | Hosting | Best for |
|----------|------|------|---------|----------|
| **ChromaDB** ✅ Used | Embedded | Free | Local | Small projects, no server |
| **Pinecone** | Cloud | Paid | Managed cloud | Production, scale |
| **Weaviate** | Self-hosted | Free | Server | Medium projects |
| **FAISS** | In-memory | Free | Local | Research, no persistence |
| **pgvector** | PostgreSQL extension | Free | Self-hosted | Already using Postgres |

**Chosen:** ChromaDB
**Why:** Already in `requirements.txt`, runs with zero setup,
stores embeddings on disk (no need to re-embed on restart),
simple Python API, perfect for academic projects.

---

## 📊 Decision Matrix: Which Technique for Which Situation?

| Situation | Best Technique | Why |
|-----------|---------------|-----|
| You have no training data | **Prompt Engineering** | Zero-shot / few-shot works immediately |
| You have 10,000+ labeled examples | **Fine-Tuning** | Model learns task-specific patterns |
| Your knowledge base changes frequently | **RAG** | No retraining needed, just update documents |
| You need the model to follow strict rules | **Prompt Engineering + Guardrails** | Explicit constraints are reliable |
| You need domain-specific terminology | **Fine-Tuning or RAG** | Depends on data availability |
| You need to cite sources for decisions | **RAG** | Retrieved chunks = traceable sources |
| You want faster inference at scale | **Fine-Tuning** | Smaller specialized model beats prompting |
| You have limited GPU / budget | **Prompt Engineering + RAG** | No training cost |

---

## 🔑 Summary for Professor

| Technique | Used in this project | Where | Type chosen |
|-----------|---------------------|-------|-------------|
| **Prompt Engineering** | ✅ Yes | Agents 1 and 3 | Role + Constraint + Iterative + Few-Shot + Chain-of-Thought |
| **Fine-Tuning** | ❌ No | — | Not used — no labeled dataset, prompt engineering sufficient |
| **RAG** | ✅ Yes | Agent 2 | Naive RAG, fixed-size chunking, dense retrieval, ChromaDB |

---

*Project: AI Return Auditor — Advanced Deep Learning Exam*
