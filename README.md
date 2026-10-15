# 🤖 AI Return Auditor

> **Visual E-Commerce Return & Refund Auditor**

AI Return Auditor is an AI-powered system designed to automate and assist the verification of e-commerce return and refund claims.

The system combines **Multimodal AI, Computer Vision, Retrieval-Augmented Generation (RAG), decision guardrails, automation, and Human-in-the-Loop** to analyze customer claims and provide transparent, evidence-based decisions.

---

## 🎯 Project Overview

When a customer requests a product return, the platform needs to determine whether the claim is consistent with the provided evidence and the company's return policy.

AI Return Auditor aims to automate this process through a multi-agent architecture.

The system analyzes:

* 📷 Product images
* 📝 Customer descriptions
* 📦 Order information
* 📚 Return and refund policies
* 🤖 AI-generated visual evidence
* 🛡️ Decision rules and guardrails

The final result can be:

* ✅ **APPROVED**
* ⚠️ **HUMAN REVIEW**

The system does not blindly trust the AI. Claims with uncertainty, inconsistencies, or insufficient evidence can be escalated to a human reviewer.

---

# 🏗️ Architecture

The project follows a **multi-agent architecture** composed of three specialized AI agents.

```text
                         ┌──────────────────────┐
                         │       Customer       │
                         │  Return Request      │
                         └──────────┬───────────┘
                                    │
                       Image + Description
                                    │
                                    ▼
                    ┌───────────────────────────┐
                    │       Agent 1             │
                    │  Multimodal Vision Agent  │
                    └─────────────┬─────────────┘
                                  │
                       Visual Evidence
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │       Agent 2             │
                    │       Policy RAG          │
                    └─────────────┬─────────────┘
                                  │
                         Relevant Policies
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │       Agent 3             │
                    │ Claim Evaluator +          │
                    │ Decision Guardrails        │
                    └─────────────┬─────────────┘
                                  │
                         ┌────────┴────────┐
                         ▼                 ▼
                    ✅ APPROVED       ⚠️ ESCALATED
                                           │
                                           ▼
                                  ┌────────────────┐
                                  │ Human Review   │
                                  └────────────────┘
```

---

# 🤖 AI Agents

## Agent 1 — Multimodal Product Damage Analyzer

The first agent analyzes the product image together with the customer's textual description.

### Input

* Product image
* Customer description

### Responsibilities

The agent identifies:

* Product category
* Product type
* Visible damage
* Damage location
* Damage severity
* Visual evidence
* Confidence score
* Description/image consistency
* Uncertainty

### Example

```text
Image:
Broken eyeglasses

Customer description:
"The shoes arrived with a stain."
```

The agent detects that the visual evidence does not correspond to the customer's description.

### Technology

* Gemini 3.1 Flash Lite
* Google Gemini API
* Multimodal AI
* Computer Vision
* Prompt Engineering
* Pydantic Structured Output
* Pillow

The agent **does not approve or reject the claim**. Its role is to provide structured visual evidence to the following agents.

---

## Agent 2 — Policy RAG Agent

The second agent retrieves the most relevant return, refund, and warranty policies from the project's knowledge base.

### Responsibilities

* Retrieve relevant policy documents
* Search the knowledge base
* Rank relevant chunks
* Provide policy evidence
* Ground the final decision in company rules

### RAG pipeline

```text
Policy Documents
       │
       ▼
Document Processing
       │
       ▼
Chunking
       │
       ▼
Embeddings
       │
       ▼
Vector Store
       │
       ▼
Similarity Search
       │
       ▼
Top-K Relevant Chunks
       │
       ▼
Policy Evidence
```

The RAG component is designed to reduce unsupported AI decisions by grounding the evaluation in the project's policy knowledge base.

---

## Agent 3 — Claim Evaluator & Decision Guardrails

The third agent combines:

* Order information
* Customer description
* Vision Agent results
* Retrieved policies
* Decision rules

It produces a final recommendation.

Possible outcomes:

```text
APPROVED
    or
HUMAN REVIEW
```

### Guardrails

The system can escalate a claim when:

* Visual evidence is inconsistent with the description
* AI confidence is too low
* Required information is missing
* Evidence is ambiguous
* Policy conditions are not clearly satisfied
* The claim presents a high-risk situation

This ensures that uncertain cases are not automatically approved.

---

# 🧑‍💼 Human-in-the-Loop

Human review is an important safety mechanism.

When the AI cannot make a sufficiently reliable decision, the claim is sent to a human reviewer.

The reviewer can:

* Approve the claim
* Reject the claim
* Request additional information
* Add comments
* Review AI evidence
* Review retrieved policies
* Inspect the decision reasoning

This creates a more trustworthy AI-assisted workflow.

---

# 🔄 Application Workflow

The Streamlit application contains five main interfaces.

```text
Home
  │
  ▼
Return Request
  │
  ├── Order information
  ├── Product information
  ├── Customer description
  └── Product image
          │
          ▼
     AI Analysis
          │
          ├── Vision Agent
          └── Policy RAG
                  │
                  ▼
              Decision
                  │
          ┌───────┴────────┐
          ▼                ▼
      APPROVED        HUMAN REVIEW
                           │
                           ▼
                    Reviewer decision
```

## Application Interfaces

### 1. Home

Presents the project and explains the AI verification workflow.

### 2. Return Request

Allows the customer or tester to provide:

* Order ID
* Product
* Category
* Purchase price
* Delivery status
* Product image
* Customer description

### 3. AI Analysis

Displays the analysis performed by the AI agents.

For the Vision Agent, the interface displays:

* Product type
* Damage type
* Damage location
* Severity
* Confidence
* Visual evidence
* Description consistency
* Uncertainty

### 4. Decision

Displays the final AI recommendation based on the available evidence and policy.

### 5. Human Review

Provides a reviewer interface for claims requiring manual verification.

---

# 🧰 Technologies

## Programming Language

* **Python 3.11+**

## Frontend / Interface

* **Streamlit**

## Artificial Intelligence

* **Google Gemini API**
* **Gemini 3.1 Flash Lite**
* **Multimodal AI**
* **Computer Vision**
* **Prompt Engineering**
* **Structured Output**

## RAG

* Document processing
* Chunking
* Embeddings
* Vector database
* Similarity search
* Top-K retrieval
* Retrieval evaluation

## Data Validation

* **Pydantic**

## Image Processing

* **Pillow**

## Configuration

* **python-dotenv**

## Automation

* **n8n**

## Development

* Git
* GitHub
* Python virtual environment

---

# 📁 Project Structure

```text
AI_Return_Auditor/
│
├── agents/
│   └── vision_agent.py
│
├── components/
│   ├── styles.py
│   ├── navbar.py
│   └── cards.py
│
├── data/
│   ├── policies/
│   └── orders/
│
├── n8n/
│   └── workflows/
│
├── prompts/
│   └── vision_agent_v1.txt
│
├── rag/
│   ├── ingestion/
│   ├── retrieval/
│   └── vector_store/
│
├── services/
│
├── views/
│   ├── __init__.py
│   ├── home.py
│   ├── return_request.py
│   ├── ai_analysis.py
│   ├── decision.py
│   └── human_review.py
│
├── app.py
├── test_vision.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

# 🔐 Environment Configuration

Create a `.env` file in the project root.

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_VISION_MODEL=gemini-3.1-flash-lite
```

**Never commit the `.env` file to GitHub.**

The `.gitignore` file contains:

```gitignore
.env
venv/
__pycache__/
*.pyc
```

---

# 🚀 Installation

## 1. Clone the repository

```bash
git clone <repository-url>
cd AI_Return_Auditor
```

## 2. Create a virtual environment

### Windows

```powershell
python -m venv venv
```

## 3. Activate the environment

```powershell
.\venv\Scripts\Activate.ps1
```

## 4. Install dependencies

```powershell
pip install -r requirements.txt
```

## 5. Configure the API key

Create:

```text
.env
```

and add:

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_VISION_MODEL=gemini-3.1-flash-lite
```

---

# ▶️ Run the Application

Start Streamlit:

```powershell
streamlit run app.py
```

The application will open in the browser.

---

# 🧪 Test the Vision Agent

Before launching the complete application, the Vision Agent can be tested independently.

```powershell
python test_vision.py
```

The test validates:

* Image loading
* Gemini API connection
* Multimodal analysis
* Structured output
* Pydantic validation
* Customer description consistency

---

# 🧪 Test the Fiscal Stamp Detection Module

Before integration into the main workflow, the fiscal stamp detection feature can be tested independently using an isolated Streamlit interface.

### 1. Run the isolated interface

To prevent port conflicts with the team's main application (running on port 8501), this module is configured to run on a dedicated port:

```powershell
streamlit run test_cachet_fiscal.py --server.port 8510
```

### 2. How to test

- Open your browser at `http://localhost:8510`.
- Drag and drop the synthetic test invoices located in the project root:

  | File                      | Expected result                                      |
  | ------------------------- | ---------------------------------------------------- |
  | `devis_avec_cachet.jpg`   | ✅ Cachet fiscal détecté — Devis **VALIDE**          |
  | `devis_sans_cachet.jpg`   | ❌ Aucun cachet fiscal détecté — Devis **INVALIDE**  |

---

# 📊 Example Vision Analysis

For an image containing damaged eyeglasses and an unrelated customer description, the Vision Agent can produce structured information such as:

```json
{
  "product_category": "Apparel & Accessories",
  "product_type": "Eyeglasses",
  "damage_type": "Broken / detached temple arm",
  "damage_location": "Hinge / temple arm",
  "severity": "High",
  "confidence": 0.98,
  "visual_evidence": "The image shows a pair of black eyeglasses with one temple arm completely detached.",
  "description_consistency": "Inconsistent",
  "uncertainty": "The customer's description does not correspond to the visual evidence."
}
```

This information is then available to the next stages of the verification workflow.

---

# 🧠 Prompt Engineering

Prompts are stored separately from the Python implementation.

Example:

```text
prompts/
└── vision_agent_v1.txt
```

The prompt defines:

* Agent role
* Responsibilities
* Forbidden decisions
* Expected output
* Severity categories
* Uncertainty handling
* Evidence requirements

Prompts are versioned to support experimentation and evaluation.

Future versions can be compared using:

```text
vision_agent_v1
vision_agent_v2
vision_agent_v3
```

This allows the project to document prompt improvements and failure fixes.

---

# 📚 RAG Knowledge Base

The RAG system will use a dedicated knowledge base containing relevant information such as:

* Return policies
* Refund conditions
* Warranty rules
* Product categories
* Return deadlines
* Damage conditions
* Exceptions

The retrieval process is designed around:

```text
Corpus
  ↓
Chunking
  ↓
Embedding
  ↓
Vector Store
  ↓
Query
  ↓
Top-K Retrieval
  ↓
Relevant Policy
  ↓
Decision Agent
```

The project will also evaluate different chunking strategies and retrieval configurations to determine which approach provides the most relevant policy context.

---

# 🔄 n8n Automation

n8n is used as the **workflow orchestration and automation layer**.

It is not considered an AI agent.

Its role is to coordinate the workflow between the application and AI components.

Example:

```text
Return Request
      ↓
n8n Workflow
      ↓
Vision Agent
      ↓
Policy RAG
      ↓
Decision Agent
      ↓
Decision
      ↓
Human Review if required
```

---

# 🛡️ Safety and Guardrails

The system is designed around the principle:

> **AI should assist the decision, not blindly make it.**

Guardrails help prevent automatic decisions when:

* Evidence is contradictory
* Confidence is insufficient
* The customer description does not match the image
* Policy information is insufficient
* Required data is missing
* The claim is ambiguous

In such cases:

```text
AI uncertainty
      ↓
Human Review
```

---

# 🎓 Academic Objectives

This project demonstrates the integration of several modern AI concepts:

* Multi-Agent Systems
* Multimodal AI
* Computer Vision
* Large Language Models
* Prompt Engineering
* Retrieval-Augmented Generation
* Embeddings
* Vector Search
* Structured AI Output
* AI Guardrails
* Human-in-the-Loop
* Workflow Automation
* Explainable AI

The project also demonstrates how these technologies can be combined into a realistic e-commerce business use case.

---

# 📌 Project Status

| Component                        | Status                  |
| -------------------------------- | ----------------------- |
| Streamlit interface              | ✅ Implemented           |
| Home interface                   | ✅ Implemented           |
| Return Request                   | ✅ Implemented           |
| Vision Agent                     | ✅ Implemented & tested  |
| Multimodal image + text analysis | ✅ Implemented           |
| Structured VisionAnalysis        | ✅ Implemented           |
| Prompt versioning                | ✅ Started               |
| Policy RAG                       | 🔄 In development       |
| Decision Agent                   | 🔄 In development       |
| Guardrails                       | 🔄 In development       |
| n8n workflow                     | 🔄 In development       |
| Human Review                     | ✅ Interface implemented |
| Retrieval evaluation             | 🔄 Planned              |
| End-to-end workflow              | 🔄 In development       |

---

# 👥 Human-in-the-Loop Principle

The project follows a hybrid AI approach:

```text
              AI
               │
       ┌───────┴───────┐
       │               │
   High confidence   Uncertainty
       │               │
       ▼               ▼
   Automatic        Human Review
   decision
```

This approach improves reliability and reduces the risk of incorrect automated refund decisions.

---

# 🎯 Future Improvements

Potential improvements include:

* Advanced RAG retrieval
* Reranking
* Retrieval evaluation metrics
* More return policy scenarios
* Better decision explanations
* Complete n8n automation
* Audit logs
* Prompt evaluation
* Confidence calibration
* Additional multimodal inputs
* Analytics dashboard
* Human reviewer feedback loop

---

# 👩‍💻 Project

**AI Return Auditor**

**Domain:** E-Commerce / Artificial Intelligence

**Main concepts:**
Multimodal AI • Computer Vision • RAG • Multi-Agent Systems • Guardrails • Human-in-the-Loop • Workflow Automation

**Built with:** Python • Streamlit • Gemini API • Pydantic • Pillow • n8n
