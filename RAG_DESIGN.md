# 📚 RAG Design — Agent 2 Policy Retrieval Agent

> **AI Return Auditor** — Advanced Deep Learning Exam
> Justification of the RAG architecture choice for Agent 2

---

## 1. Problem Statement

Agent 2 must answer one question at query time:

> *Given a structured damage analysis produced by Agent 1, which return/refund/warranty
> policy applies to this claim, and what does it say?*

The agent does **not** decide the outcome. It only retrieves and summarizes
the relevant policy so Agent 3 can make a justified, grounded decision.

---

## 2. RAG Types Considered

Six RAG architectures were evaluated. The table below summarizes why each
was accepted or rejected for this specific use case.

| RAG Type | Core Mechanism | Decision | Reason |
|---|---|---|---|
| **Naive RAG** | Embed query → Top-K → Generate | ❌ Rejected | No query optimization. Raw customer text is a poor search query. No modules to justify in the report. |
| **Advanced RAG** | Fixed pipeline: rewrite → retrieve → rerank → generate | ⚠️ Close, but rejected | Still a fixed pipeline. Every query goes through every step regardless of context. No flexibility. |
| **Modular RAG** | Pick and combine modules per problem | ✅ **Chosen** | Lets us justify each module individually. Matches the problem without over-engineering. |
| **Corrective RAG (CRAG)** | Retrieve → evaluate quality → fall back to web search | ❌ Rejected | Fallback never triggers. 3 static files cover all possible queries. Dead code. |
| **Self-RAG** | Model decides token-by-token whether to retrieve | ❌ Rejected | Requires a specially fine-tuned model with special tokens. Not compatible with Gemini API. |
| **Agentic RAG** | Agent plans multi-hop retrieval across sources | ❌ Rejected | Designed for large, heterogeneous knowledge bases. 3 policy files do not justify this complexity. |

---

## 3. Why Modular RAG

### 3.1 Design Philosophy

Modular RAG is not a fixed pipeline. It is a **composition framework**:
select only the modules that solve real problems in your specific use case,
combine them deliberately, and justify each one.

The exam explicitly requires:
> *"Justify the chunking strategy, the embedding model, the retrieval setup,
> the architecture you chose."*

A fixed pipeline (Naive or Advanced RAG) gives nothing to justify beyond
"we followed the standard recipe." Modular RAG forces deliberate choices.

---

### 3.2 Modules Selected and Why

```
VisionAnalysis (Agent 1 output)
         │
         ▼
┌─────────────────────────┐
│  Module 1               │
│  Query Rewriting        │  ← Prompt engineering (pre-retrieval)
└────────────┬────────────┘
             │  Optimized search query
             ▼
┌─────────────────────────┐
│  Module 2               │
│  Dense Retrieval        │  ← ChromaDB + sentence-transformers
└────────────┬────────────┘
             │  Top-5 candidate chunks
             ▼
┌─────────────────────────┐
│  Module 3               │
│  Reranking              │  ← Cross-encoder reranks Top-5 → Top-3
└────────────┬────────────┘
             │  Top-3 reranked chunks
             ▼
┌─────────────────────────┐
│  Module 4               │
│  Context Compression    │  ← Remove noise, keep relevant sentences
└────────────┬────────────┘
             │
             ▼
       PolicyResult
  (chunks + sources + scores)
         │
         ▼
      Agent 3
```

---

#### Module 1 — Query Rewriting (Pre-Retrieval Prompt Engineering)

**Problem it solves:**
The raw customer description ("my shoes arrived with a stain") is not
an optimal retrieval query. It is informal, imprecise, and may not match
the terminology used in policy documents ("visible defects", "cosmetic damage").

**Solution:**
A prompt transforms the structured `VisionAnalysis` output from Agent 1
into a precise, policy-oriented search query before embedding.

```
Input:  damage_type="stain", product_type="running shoes",
        severity="Medium", description_consistency="Consistent"

Output: "Return policy for running shoes received with cosmetic
         stain damage, medium severity, within return window"
```

**Why this matters:**
The VisionAnalysis is already structured. It contains exactly the fields
needed to build a high-quality search query. Not using them would be
wasting the output of Agent 1.

---

#### Module 2 — Dense Retrieval (ChromaDB + all-MiniLM-L6-v2)

**Problem it solves:**
Keyword search would miss semantically equivalent terms.
"Visible defects" and "product damage" mean the same thing
but share no keywords.

**Solution:**
Dense vector retrieval with cosine similarity captures semantic meaning,
not just keyword overlap. The embedding model converts both the query
and policy chunks into 384-dimensional vectors. Similarity is measured
by the angle between them (cosine), not magnitude.

**Model choice:** `all-MiniLM-L6-v2`
- Free, runs offline, no API key required
- 384 dimensions — sufficient for short policy paragraphs
- Already installed via `sentence-transformers`
- Fast inference, lightweight

**Why not a larger model?**
Policy chunks are short (≤ 500 characters). Larger models add latency
and cost without meaningful quality improvement at this scale.

---

#### Module 3 — Reranking (Cross-Encoder)

**Problem it solves:**
Bi-encoder retrieval (Module 2) is fast but approximate. The Top-5
results are not always ranked in the optimal order because the query
and document were embedded independently.

**Solution:**
A cross-encoder model receives each `(query, chunk)` pair together
and produces a relevance score. This joint encoding is more accurate
than cosine similarity but too slow to run on the entire knowledge base
(which is why it runs only on the Top-5 shortlist from Module 2).

**Pipeline:** Top-5 from bi-encoder → Cross-encoder reranking → Top-3

**Why reranking matters here:**
Return, refund, and warranty policies often have overlapping language.
A stain on a shoe might match chunks from all 3 policy files.
Reranking ensures the most applicable chunk is ranked first.

---

#### Module 4 — Context Compression

**Problem it solves:**
Full chunks (up to 500 characters) often contain sentences that are
not relevant to the specific query. Injecting all of them into Agent 3's
prompt adds noise and increases token usage.

**Solution:**
After reranking, only sentences directly relevant to the query are
extracted from each chunk. The compressed context is what Agent 3
receives — precise, cited, noise-free.

---

### 3.3 Why Not Advanced RAG?

Advanced RAG would also include query rewriting and reranking,
but as a **fixed sequence applied to every query**.

The distinction in Modular RAG is that each module is:
1. **Independently justified** (not just "we followed the pipeline")
2. **Replaceable** — if the knowledge base grows, we can add hybrid search
   (BM25 + dense) as a new module without rewriting the pipeline
3. **Conditional** — the fallback path (return all chunks if reranking fails)
   is a module-level decision, not a pipeline failure

For the exam, the ability to justify each module individually is the
stronger academic position.

---

### 3.4 Why Not Agentic RAG?

Agentic RAG is the correct choice when:
- The knowledge base spans multiple heterogeneous sources
- Multi-hop retrieval is needed (retrieve A, use A to query B)
- The agent must decide whether to retrieve at all

None of these apply here:
- 3 static `.txt` files, all the same format
- Single-hop retrieval always suffices
- Retrieval is always needed (every claim needs a policy)

Building an agentic retriever here would be complexity without benefit,
and the exam rewards justified simplicity over unjustified complexity.

---

## 4. Chunking Strategy

### Choice: Fixed-Size Chunking with Overlap

| Parameter | Value | Justification |
|---|---|---|
| Chunk size | 500 characters | Policy rules are short paragraphs. Larger chunks add noise. |
| Overlap | 100 characters | Prevents a rule from being split across two chunks. |
| Strategy | Fixed-size | Policy documents are already structured as short rules. Semantic chunking adds complexity without benefit at this scale. |

### Comparison with Semantic Chunking

| Criterion | Fixed-Size (500/100) | Semantic Chunking |
|---|---|---|
| Implementation complexity | Low | High (requires embedding similarity computation) |
| Quality for short policy docs | Good | Marginally better |
| Explainability | Simple to justify | Harder to explain |
| Exam value | Justified choice | Over-engineered for 3 files |

**Decision:** Fixed-size chunking is the correct baseline for this knowledge base.
Semantic chunking would be the next step if the knowledge base grew to
hundreds of documents with variable structure.

---

## 5. Prompt Engineering in Agent 2

Prompt engineering is applied at **two points** in the pipeline:

### 5.1 Pre-Retrieval: Query Rewriting Prompt

Converts the structured `VisionAnalysis` into an optimized search query.

**Technique:** Role prompting + structured output + constraint prompting

```
File: prompts/rag_agent_v1.txt (query rewriting section)

Role: "You are a policy retrieval specialist..."
Constraint: "Output only the search query, no explanation."
Structure: Single sentence, policy-oriented terminology
```

### 5.2 Post-Retrieval: Policy Synthesis Prompt

After retrieval, Agent 2 synthesizes the retrieved chunks into a
structured `PolicyResult` that Agent 3 can consume directly.

**Technique:** Chain-of-thought + role prompting + output formatting

```
File: prompts/rag_agent_v1.txt (synthesis section)

Role: "You are the Policy Retrieval Agent. Your role is ONLY
       to retrieve and summarize applicable policies."
CoT:  Step 1: Identify applicable policy
      Step 2: Extract relevant conditions
      Step 3: Note exceptions
      Step 4: Output structured result
Constraint: "Do NOT approve or reject the claim."
```

---

## 6. Why Not Fine-Tuning?

| Criterion | Fine-Tuning | RAG (chosen) |
|---|---|---|
| Training data needed | Thousands of `{query → correct chunk}` pairs | Zero |
| Policy update cost | Retrain model + redeploy | Edit `.txt` file |
| Explainability | Black box (knowledge in weights) | Retrieved chunks are citable |
| Cost | GPU + API credits | Free (local ChromaDB) |
| Latency | Fast inference | Slightly slower (retrieval step) |

**Key argument:** Policies change. Fine-tuning bakes knowledge into model weights
permanently. RAG reads the live document at inference time. For a system
where return windows, warranty conditions, and refund rules can change monthly,
RAG is the architecturally correct choice regardless of quality comparisons.

---

## 7. Retrieval Evaluation Plan

To satisfy the exam requirement for retrieval evaluation:

| Test query | Expected top chunk | Metric |
|---|---|---|
| "shoes received with visible stain" | return_policy: visible defects clause | Hit@1 |
| "broken product within warranty period" | warranty_policy: manufacturing defect | Hit@1 |
| "refund for item returned after 30 days" | refund_policy: return window exception | Hit@3 |
| "product damaged during shipping" | return_policy: shipping damage clause | Hit@1 |
| "no visible damage but wrong item" | return_policy: wrong item clause | Hit@3 |

**Metrics used:** Hit@1, Hit@3, MRR (Mean Reciprocal Rank)

A comparison between fixed-size chunking (500/100) and a larger chunk size
(1000/200) will be run on these queries to demonstrate retrieval quality difference.

---

## 8. Technology Stack Summary

| Component | Technology | Justification |
|---|---|---|
| Vector store | ChromaDB | Local, persistent, zero setup, free |
| Embedding model | all-MiniLM-L6-v2 | Free, offline, 384 dims, sufficient for policy text |
| Reranker | cross-encoder/ms-marco-MiniLM-L-6-v2 | Free, offline, accurate for short texts |
| LLM (synthesis) | Gemini Flash | Already used in Agent 1, consistent stack |
| Chunking | LangChain RecursiveCharacterTextSplitter | Reliable, configurable, well-documented |

---

*Project: AI Return Auditor — Advanced Deep Learning Exam*
*RAG Architecture: Modular RAG (Query Rewriting + Dense Retrieval + Reranking + Compression)*
