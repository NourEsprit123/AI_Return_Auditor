# AI Return Auditor

AI Return Auditor is a local prototype for reviewing e-commerce return claims. A customer submits order details, a description, and a product photo in the Streamlit app. n8n coordinates the processing stages hosted by FastAPI:

1. **Photo review** compares the image with the customer’s description using Gemini.
2. **Policy matching** retrieves relevant passages from the local policy corpus.
3. **Recommendation** samples a Groq model five times, applies consensus and business guardrails, then checks the result with a local Ollama model.
4. **Response** returns the recommendation or an escalation status to the UI.

This project provides a recommendation; it does not issue a refund, create a return label, or connect to an order-management system. Receipt OCR is not integrated yet.

For implementation details, data flow, model behavior, limitations, and the complete n8n workflow, see [PROJECT_REPORT.md](./PROJECT_REPORT.md).

## Requirements

- Windows 10/11, macOS, or Linux.
- Python **3.11** recommended.
- Git.
- Gemini API key and Groq API key.
- Ollama installed locally, with `qwen2.5:7b` downloaded.
- n8n running locally. Docker Desktop is recommended for Windows.
- Internet access for API calls and first-time download of Python/model dependencies.

The retrieval embedding and reranking models are downloaded the first time the RAG stage runs. They may require several gigabytes of storage and can make the first request take longer.

## 1. Get the project and install Python dependencies

Open PowerShell (or a terminal) in the directory where you want the project:

```powershell
git clone <repository-url> AI_Return_Auditor
cd AI_Return_Auditor

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On macOS or Linux, create and activate the environment with:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, either allow local scripts for your user:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

or activate from Command Prompt instead:

```bat
.venv\Scripts\activate.bat
```

Use the same virtual environment when running both FastAPI and Streamlit.

## 2. Configure API keys and local services

Copy the example file and edit it:

```powershell
Copy-Item .env.example .env
notepad .env
```

Set your own credentials in `.env`:

```dotenv
GEMINI_API_KEY=replace-with-your-gemini-api-key
GROQ_API_KEY=replace-with-your-groq-api-key
```

The remaining values in `.env.example` select the current model and local service addresses. Never commit `.env` or share its contents.

### Start Ollama and download the judge model

Install Ollama from [ollama.com](https://ollama.com/) and download the configured model:

```powershell
ollama pull qwen2.5:7b
ollama run qwen2.5:7b
```

Ollama generally keeps its local service running after the model command starts. Leave the service available while processing claims. The FastAPI backend calls Ollama at `http://127.0.0.1:11434`; the judge intentionally requires a loopback URL.

### Start n8n

With Docker Desktop running, create persistent storage and start n8n:

```powershell
docker volume create n8n_data
docker run -d --name n8n -p 5678:5678 -v n8n_data:/home/node/.n8n docker.n8n.io/n8nio/n8n
```

Open [http://localhost:5678](http://localhost:5678), complete the initial n8n setup, and import the workflow:

1. In n8n, choose **Import from File**.
2. Select `n8n/workflow.json` from this project.
3. Save and **activate** the imported workflow.
4. Confirm its HTTP Request nodes use `http://host.docker.internal:8000` to call FastAPI.

The checked-in workflow export is inactive by default. The production webhook is `http://localhost:5678/webhook/return-claim`. A `/webhook-test/return-claim` URL works only while the Webhook node is listening for a test event. Re-import or update the n8n workflow when the local JSON changes; editing the file does not update an already-imported workflow.

If you already have n8n installed outside Docker, you can use that instance instead. Ensure it can reach FastAPI at the backend address configured in the workflow.

## 3. Run the application

Keep Ollama and n8n running. Open two PowerShell terminals in `AI_Return_Auditor`, activate `.venv` in each, and run:

**Terminal 1 — FastAPI agent backend**

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn appBack:app --host 0.0.0.0 --port 8000
```

Binding to `0.0.0.0` allows the n8n Docker container to reach the backend through `host.docker.internal`. Do not expose this development server to an untrusted network.

**Terminal 2 — Streamlit client**

```powershell
.\.venv\Scripts\Activate.ps1
streamlit run appUI.py
```

Open the local URL printed by Streamlit, usually [http://localhost:8501](http://localhost:8501). The UI defaults to the n8n production webhook at `http://localhost:5678/webhook/return-claim` and progress endpoint at `http://127.0.0.1:8000`.

The complete request can take several minutes, especially during the first retrieval-model load. The UI allows up to 30 minutes for the n8n response; the RAG and decision HTTP Request nodes each allow up to 10 minutes.

## 4. Check service health and test a claim

In another terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Expected response:

```text
status
------
ok
```

Then submit a claim through the Streamlit app with a non-empty order number, description, and a PNG/JPG product image. Watch the execution in n8n and the stage progress in the app.

The recommendation is shown in the UI. The local compliance report is written to `llm_judge_verdict.json`; it is an internal diagnostic file and is not part of the customer result. The UI also stores local claim history in `audit_log.json`.

## Configuration reference

| Variable | Purpose | Default / example |
|---|---|---|
| `GEMINI_API_KEY` | Gemini Vision API credential. | Required. |
| `GEMINI_VISION_MODEL` | Preferred image model. | `gemini-3.8-flash`; code has fallback model names. |
| `GROQ_API_KEY` | Groq credential used by query expansion and decision sampling. | Required. |
| `OLLAMA_BASE_URL` | Local Ollama base URL. | `http://127.0.0.1:11434` |
| `OLLAMA_MODEL` | Local compliance judge model. | `qwen2.5:7b` |
| `OLLAMA_TIMEOUT_SECONDS` | Judge request timeout. | `300` |
| `N8N_WEBHOOK_URL` | Webhook used by the Streamlit client. | `http://localhost:5678/webhook/return-claim` |
| `AUDIT_BACKEND_URL` | FastAPI base URL used for progress polling. | `http://127.0.0.1:8000` |
| `AUDIT_LOG_PATH` | Path to local UI history. | `audit_log.json` |

The FastAPI process loads `.env`. Streamlit uses the documented local URL defaults; if running services on other addresses, set `N8N_WEBHOOK_URL` and `AUDIT_BACKEND_URL` in the environment before launching Streamlit.

## Troubleshooting

### `The requested webhook "POST return-claim" is not registered`

Import and activate the workflow in n8n, then use the production URL:

```text
http://localhost:5678/webhook/return-claim
```

For a temporary editor test, click **Listen for test event** and submit using `/webhook-test/return-claim` while it is listening.

### n8n reports connection refused for `127.0.0.1:8000`

Inside a Docker container, `127.0.0.1` refers to the container, not the Windows host. Verify the workflow HTTP nodes use:

```text
http://host.docker.internal:8000
```

Also verify FastAPI is running with `--host 0.0.0.0`, and that Windows Firewall permits the local Docker-to-host connection.

### Vision or decision endpoint reports a missing API key

Check that `.env` exists in `AI_Return_Auditor`, contains the correct `GEMINI_API_KEY` and `GROQ_API_KEY`, and restart FastAPI after editing it.

### Judge fails or Ollama connection is refused

Confirm Ollama is running, the model is present (`ollama list`), and `.env` contains:

```dotenv
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:7b
```

The decision stage fails closed if the judge cannot produce and save a valid verdict; it does not return the unchecked consensus as a successful result.

### RAG stage is slow or times out

The first request may download and initialize the embedding and reranker models. Confirm internet access, sufficient disk space and memory, then retry. Check the n8n RAG HTTP Request node timeout is `600000` milliseconds. Do not assume a longer timeout fixes a backend crash or unavailable model service.

### `ModuleNotFoundError` or install errors

Activate the project virtual environment and run `python -m pip install -r requirements.txt`. If a package fails to build, use Python 3.11 and consult that package’s platform-specific installation instructions.

## Workflow and implementation details

The importable workflow is [`n8n/workflow.json`](./n8n/workflow.json). It calls FastAPI in order:

```text
Webhook → Vision → RAG → merge claim + evidence → Decision + Judge → response
```

The IF node returns an escalation response when the final decision is `ESCALATE_HUMAN`. This branch does not create a staffed review ticket; human review remains a recommendation/status, not a completed operational process.

The detailed [project report](./PROJECT_REPORT.md) describes request shapes, retrieval and consensus behavior, privacy considerations, and known limitations.

## Security and data handling

- Use test claims and sample photos for development. This prototype has no user authentication or access control.
- FastAPI’s stage endpoints are unauthenticated. Keep the backend on trusted local development networks only.
- Do not commit `.env`, `audit_log.json`, or `llm_judge_verdict.json`; the latter two may contain claim-related data.
- The judge report is a shared overwrite file. Concurrent requests can overwrite one another’s report.
- No explicit upload-size limit, production retention policy, or automated security controls are currently configured.
- Recommendations should be reviewed by a human before being used for real customer decisions.

## Current implementation status

- Implemented: Streamlit client, FastAPI stage endpoints, Gemini Vision, policy retrieval, Groq self-consistency decision, local Ollama compliance judge, and n8n orchestration export.
- Not integrated: receipt OCR, order/payment system actions, and a real human-review queue.
- Deployment note: the n8n JSON export is inactive by default and must be imported and activated in your own n8n instance.
