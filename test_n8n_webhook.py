"""
test_n8n_webhook.py
-------------------
Sends a real claim to the n8n webhook end-to-end.

Prerequisites:
  1. FastAPI server running:  uvicorn services.api:app --host 0.0.0.0 --port 8000
  2. n8n running:             n8n start
  3. Workflow imported and activated in n8n

The webhook URL is: http://localhost:5678/webhook/return-claim
"""

import requests
import base64
import json
import sys
from pathlib import Path

# ============================================================
# CONFIGURATION
# ============================================================

N8N_WEBHOOK_URL = "http://localhost:5678/webhook/return-claim"
FASTAPI_URL     = "http://localhost:8000"
IMAGE_PATH      = Path("glasses.PNG")

# ============================================================
# CHECKS
# ============================================================

print("=" * 60)
print("AI Return Auditor — n8n Webhook Test")
print("=" * 60)

# Check FastAPI is up
try:
    r = requests.get(f"{FASTAPI_URL}/health", timeout=5)
    if r.status_code == 200:
        print(f"[OK] FastAPI server is running at {FASTAPI_URL}")
    else:
        print(f"[WARN] FastAPI responded with status {r.status_code}")
except Exception:
    print(f"[ERROR] FastAPI server not reachable at {FASTAPI_URL}")
    print("        Run: uvicorn services.api:app --host 0.0.0.0 --port 8000")
    sys.exit(1)

# Check n8n is up
try:
    r = requests.get("http://localhost:5678", timeout=5)
    print(f"[OK] n8n is running at http://localhost:5678")
except Exception:
    print(f"[ERROR] n8n not reachable at http://localhost:5678")
    print("        Run: n8n start")
    sys.exit(1)

# Check image exists
if not IMAGE_PATH.exists():
    print(f"[ERROR] Image not found: {IMAGE_PATH}")
    sys.exit(1)

print()

# ============================================================
# BUILD PAYLOAD
# ============================================================

with open(IMAGE_PATH, "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode()

payload = {
    "image_base64":       image_b64,
    "customer_description": "The shoes I ordered arrived with a stain on them.",
    "order_id":           "ORD-003",
    "product_name":       "Ray-Ban Wayfarer",
    "product_category":   "Accessories",
    "purchase_price":     165.0,
    "delivery_status":    "Delivered",
}

print("Sending claim to n8n webhook...")
print(f"  Order ID    : {payload['order_id']}")
print(f"  Product     : {payload['product_name']}")
print(f"  Description : {payload['customer_description']}")
print(f"  Image       : {IMAGE_PATH.name}")
print()

# ============================================================
# SEND TO N8N
# ============================================================

try:
    response = requests.post(
        N8N_WEBHOOK_URL,
        json=payload,
        timeout=180,
    )

    print(f"n8n response status : {response.status_code}")
    print()

    if response.status_code == 200:
        result = response.json()

        print("=" * 60)
        print("PIPELINE RESULT")
        print("=" * 60)

        decision = result.get("decision", {})
        print(f"Decision   : {decision.get('decision', 'N/A')}")
        print(f"Confidence : {decision.get('confidence', 0):.0%}")
        print(f"Risk       : {decision.get('risk_level', 'N/A')}")
        print(f"Guardrail  : {decision.get('guardrail_hit', 'N/A')}")
        print(f"Reason     : {decision.get('reason', 'N/A')[:200]}")

        print()
        print("Evidence chain:")
        for e in decision.get("evidence_chain", []):
            print(f"  • {e}")

        print()
        vision = result.get("vision", {})
        print("Vision Agent:")
        print(f"  Product  : {vision.get('product_type', 'N/A')}")
        print(f"  Damage   : {vision.get('damage_type', 'N/A')}")
        print(f"  Severity : {vision.get('severity', 'N/A')}")
        print(f"  Conf     : {vision.get('confidence', 0):.0%}")

        print()
        rag = result.get("rag", {})
        print("RAG Agent:")
        print(f"  Policy   : {rag.get('applicable_policy', 'N/A')}")
        print(f"  Summary  : {rag.get('summary', 'N/A')[:150]}")

    else:
        print("Response body:")
        print(response.text[:500])

except requests.exceptions.Timeout:
    print("[ERROR] Request timed out. The pipeline took too long.")
    print("        Check that both FastAPI and n8n are running.")
except Exception as exc:
    print(f"[ERROR] {exc}")

print()
print("=" * 60)
print("DONE")
print("=" * 60)
