import os
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

import base64
import requests
import streamlit as st
from io import BytesIO
from PIL import Image

from components.styles import apply_styles
from components.navbar import render_navbar, render_navigation

# ============================================================
# N8N WEBHOOK URL
# ============================================================
N8N_WEBHOOK_URL = "http://localhost:5678/webhook/return-claim"
N8N_TIMEOUT     = 180  # seconds


def show_ai_analysis():

    apply_styles()
    render_navbar()
    render_navigation()

    st.write("")

    st.caption("AI ANALYSIS  /  STEP 02")
    st.markdown("# Intelligence is analyzing your claim.")
    st.write(
        "The claim is sent to n8n, which orchestrates the full pipeline: "
        "Vision Agent → RAG Agent → Decision Agent."
    )
    st.write("")

    # ==========================================================
    # CLAIM INFORMATION
    # ==========================================================

    order_id      = st.session_state.get("order_id", "—")
    product_name  = st.session_state.get("product_name", "Unknown product")
    category      = st.session_state.get("product_category", "Unknown")
    description   = st.session_state.get("description", "")
    image_bytes   = st.session_state.get("image_bytes")

    with st.container(border=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.caption("ORDER")
            st.markdown(f"**{order_id}**")
        with col2:
            st.caption("PRODUCT")
            st.markdown(f"**{product_name}**")
        with col3:
            st.caption("CATEGORY")
            st.markdown(f"**{category}**")
        with col4:
            st.caption("PIPELINE")
            st.info("n8n → 3 AGENTS")

    st.write("")

    # ==========================================================
    # VALIDATION
    # ==========================================================

    if image_bytes is None:
        st.error("No image was provided. Please return to the Return Request page.")
        if st.button("← Back to return request", key="back_to_request"):
            st.session_state.page = "Return Request"
            st.rerun()
        return

    if not description.strip():
        st.error("No customer description was provided.")
        if st.button("← Back to return request", key="back_to_request_desc"):
            st.session_state.page = "Return Request"
            st.rerun()
        return

    # ==========================================================
    # LOAD IMAGE FOR DISPLAY
    # ==========================================================

    try:
        image = Image.open(BytesIO(image_bytes))
        image.load()
        image = image.convert("RGB")
    except Exception as exc:
        st.error(f"Unable to read the uploaded image: {exc}")
        return

    # ==========================================================
    # RUN PIPELINE VIA N8N
    # ==========================================================

    pipeline_done = (
        "vision_result" in st.session_state
        and "rag_result"      in st.session_state
        and "decision_result" in st.session_state
    )

    if not pipeline_done:

        left, right = st.columns([0.9, 1.1], gap="large")

        with left:
            with st.container(border=True):
                st.caption("VISUAL EVIDENCE")
                st.image(image, caption="Customer-provided image", use_container_width=True)

        with right:
            with st.container(border=True):
                st.caption("CUSTOMER DESCRIPTION")
                st.markdown("### 💬 What the customer reported")
                st.info(description)
                st.write("")
                st.caption("ORCHESTRATION")
                st.write("🔗 Streamlit → **n8n webhook**")
                st.write("   ↳ Agent 1 → Vision analysis")
                st.write("   ↳ Agent 2 → Policy retrieval")
                st.write("   ↳ Agent 3 → Decision evaluation")

        st.write("")

        col1, col2, col3 = st.columns([1, 1.5, 1])

        with col2:
            if st.button("🔍  Run Full AI Pipeline", use_container_width=True, key="run_pipeline"):

                # Check n8n is running
                try:
                    requests.get("http://localhost:5678", timeout=3)
                except Exception:
                    st.error(
                        "❌ n8n is not running. Please start it with: `n8n start`"
                    )
                    return

                # Check FastAPI is running
                try:
                    requests.get("http://localhost:8000/health", timeout=3)
                except Exception:
                    st.error(
                        "❌ FastAPI server is not running. "
                        "Please start it with: `uvicorn services.api:app --host 0.0.0.0 --port 8000`"
                    )
                    return

                # Build payload
                image_b64 = base64.b64encode(image_bytes).decode()

                payload = {
                    "image_base64":        image_b64,
                    "customer_description": description,
                    "order_id":            str(st.session_state.get("order_id", "")),
                    "product_name":        str(st.session_state.get("product_name", "")),
                    "product_category":    str(st.session_state.get("product_category", "")),
                    "purchase_price":      float(st.session_state.get("purchase_price", 0.0)),
                    "delivery_status":     str(st.session_state.get("delivery_status", "Delivered")),
                }

                with st.status("Running AI pipeline via n8n...", expanded=True) as status:

                    st.write("📡 Sending claim to n8n webhook...")
                    st.write(f"   URL: {N8N_WEBHOOK_URL}")

                    try:
                        response = requests.post(
                            N8N_WEBHOOK_URL,
                            json=payload,
                            timeout=N8N_TIMEOUT,
                        )

                        if response.status_code != 200:
                            st.error(f"n8n returned status {response.status_code}: {response.text[:300]}")
                            return

                        # n8n may return a list or a dict — handle both
                        raw = response.json()
                        if isinstance(raw, list):
                            result = raw[0] if raw else {}
                        elif isinstance(raw, str):
                            import json
                            result = json.loads(raw)
                        else:
                            result = raw

                        # ---- Store Vision result ----
                        st.write("✓ Agent 1 — Vision Agent completed")
                        # Handle both nested {"vision": {...}} and flat format
                        if "vision" in result and isinstance(result["vision"], dict):
                            vision = result["vision"]
                        else:
                            # flat format from old respond nodes
                            vision = {
                                "product_type":            result.get("vision_product", ""),
                                "damage_type":             result.get("vision_damage", ""),
                                "severity":                result.get("vision_severity", ""),
                                "confidence":              result.get("confidence", 0),
                                "product_category":        result.get("product_category", ""),
                                "damage_location":         result.get("damage_location", ""),
                                "visual_evidence":         result.get("visual_evidence", ""),
                                "description_consistency": result.get("description_consistency", "Consistent"),
                                "uncertainty":             result.get("uncertainty", ""),
                            }
                        st.session_state.vision_result = {
                            "product_category":        vision.get("product_category", ""),
                            "product_type":            vision.get("product_type", ""),
                            "damage_type":             vision.get("damage_type", ""),
                            "damage_location":         vision.get("damage_location", ""),
                            "severity":                vision.get("severity", ""),
                            "confidence":              float(vision.get("confidence", 0)),
                            "visual_evidence":         vision.get("visual_evidence", ""),
                            "description_consistency": vision.get("description_consistency", ""),
                            "uncertainty":             vision.get("uncertainty", ""),
                        }

                        # ---- Store RAG result ----
                        st.write("✓ Agent 2 — RAG Agent completed")
                        if "rag" in result and isinstance(result["rag"], dict):
                            rag = result["rag"]
                        else:
                            rag = {
                                "query":               result.get("rag_query", ""),
                                "applicable_policy":   result.get("applicable_policy", ""),
                                "summary":             result.get("policy_summary", ""),
                                "sources":             result.get("sources", []),
                                "retrieval_successful": True,
                                "chunks":              [],
                            }
                        st.session_state.rag_result = {
                            "query":               rag.get("query", ""),
                            "applicable_policy":   rag.get("applicable_policy", ""),
                            "summary":             rag.get("summary", ""),
                            "sources":             rag.get("sources", []),
                            "retrieval_successful": rag.get("retrieval_successful", True),
                            "chunks":              rag.get("chunks", []),
                        }

                        # ---- Store Decision result ----
                        st.write("✓ Agent 3 — Decision Agent completed")
                        if "decision" in result and isinstance(result["decision"], dict):
                            dec = result["decision"]
                        else:
                            dec = {
                                "decision":        result.get("decision", "HUMAN_REVIEW"),
                                "confidence":      result.get("confidence", 0),
                                "risk_level":      result.get("risk_level", "MEDIUM"),
                                "reason":          result.get("reason", ""),
                                "guardrail_hit":   result.get("guardrail_hit", "None"),
                                "evidence_chain":  result.get("evidence_chain", []),
                                "reasoning_steps": result.get("reasoning_steps", ""),
                            }
                        st.session_state.decision_result = {
                            "decision":        dec.get("decision", "HUMAN_REVIEW"),
                            "confidence":      float(dec.get("confidence", 0)),
                            "risk_level":      dec.get("risk_level", "MEDIUM"),
                            "reason":          dec.get("reason", ""),
                            "guardrail_hit":   dec.get("guardrail_hit", "None"),
                            "evidence_chain":  dec.get("evidence_chain", []),
                            "reasoning_steps": dec.get("reasoning_steps", ""),
                        }

                        status.update(label="✓ n8n pipeline complete", state="complete")

                    except requests.exceptions.Timeout:
                        st.error(
                            "⏱ The pipeline timed out. "
                            "Gemini may be under high demand. Please try again."
                        )
                        return
                    except Exception as exc:
                        st.error(f"Pipeline failed: {exc}")
                        return

                st.success("✓ All 3 agents completed via n8n orchestration.")
                st.rerun()

        return

    # ==========================================================
    # DISPLAY RESULTS
    # ==========================================================

    vision   = st.session_state.get("vision_result", {})
    rag      = st.session_state.get("rag_result", {})
    decision = st.session_state.get("decision_result", {})

    confidence  = float(vision.get("confidence", 0))
    severity    = vision.get("severity", "Unknown")
    consistency = vision.get("description_consistency", "Unknown")

    # ==========================================================
    # PIPELINE STATUS
    # ==========================================================

    st.caption("PIPELINE  /  COMPLETED  —  Orchestrated by n8n")
    st.markdown("## All 3 agents completed")
    st.write("")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.success(f"✓ Vision — {confidence:.0%} confidence")
    with col2:
        st.success(f"✓ Policy — {rag.get('applicable_policy', 'Retrieved')}")
    with col3:
        dec = decision.get("decision", "—")
        if dec == "APPROVED":
            st.success(f"✓ Decision — {dec}")
        else:
            st.warning(f"⚠ Decision — {dec}")

    st.write("")

    # ==========================================================
    # VISION SECTION
    # ==========================================================

    st.divider()
    st.caption("AGENT 1 — VISION AGENT")
    st.markdown("## 👁️ Visual damage analysis")
    st.write("")

    with st.container(border=True):
        col1, col2, col3 = st.columns([1.2, 0.8, 1.2])
        with col1:
            st.caption("VISION CONFIDENCE")
            st.markdown(f"# {confidence*100:.0f}%")
            st.progress(max(0.0, min(confidence, 1.0)))
        with col2:
            st.caption("SEVERITY")
            sev = severity.lower()
            if sev == "high":     st.error(f"⚠ {severity}")
            elif sev == "medium": st.warning(f"⚠ {severity}")
            elif sev == "low":    st.info(f"● {severity}")
            else:                 st.info(f"● {severity}")
        with col3:
            st.caption("DESCRIPTION CONSISTENCY")
            if "consistent" in consistency.lower() and "inconsistent" not in consistency.lower():
                st.success("✓ CONSISTENT")
            else:
                st.warning("⚠ INCONSISTENT")

    st.write("")

    left, right = st.columns([0.9, 1.1], gap="large")

    with left:
        with st.container(border=True):
            st.caption("VISUAL EVIDENCE")
            st.image(image, caption="Analyzed product", use_container_width=True)

    with right:
        with st.container(border=True):
            st.caption("DETECTED ATTRIBUTES")
            st.markdown("### AI observations")
            col1, col2 = st.columns(2)
            with col1:
                st.caption("PRODUCT TYPE")
                st.write(vision.get("product_type", "Unknown"))
            with col2:
                st.caption("CATEGORY")
                st.write(vision.get("product_category", "Unknown"))
            st.divider()
            st.markdown("**DAMAGE TYPE**")
            st.write(vision.get("damage_type", "Unknown"))
            st.write("")
            st.markdown("**DAMAGE LOCATION**")
            st.write(vision.get("damage_location", "Unknown"))

    st.write("")

    with st.container(border=True):
        st.caption("VISUAL EVIDENCE DESCRIPTION")
        st.write(vision.get("visual_evidence", "—"))

    with st.container(border=True):
        st.caption("DESCRIPTION CONSISTENCY")
        if "consistent" in consistency.lower() and "inconsistent" not in consistency.lower():
            st.success(consistency)
        else:
            st.warning(consistency)

    with st.container(border=True):
        st.caption("MODEL UNCERTAINTY")
        st.write(vision.get("uncertainty", "None"))

    # ==========================================================
    # RAG SECTION
    # ==========================================================

    st.write("")
    st.divider()
    st.caption("AGENT 2 — POLICY RAG AGENT")
    st.markdown("## 📚 Policy retrieval")
    st.write("")

    with st.container(border=True):
        col1, col2 = st.columns([2, 1])
        with col1:
            st.caption("APPLICABLE POLICY")
            st.markdown(f"### {rag.get('applicable_policy', '—')}")
            st.write(rag.get("summary", "—"))
        with col2:
            st.caption("SOURCES")
            for s in rag.get("sources", []):
                st.info(s)

    st.write("")

    chunks = rag.get("chunks", [])
    if chunks:
        st.caption("RETRIEVED CHUNKS")
        for i, chunk in enumerate(chunks):
            score = chunk.get("relevance_score", 0)
            with st.expander(f"Chunk {i+1} — {chunk.get('doc_type','Policy')} | score={score:.3f}"):
                st.write(chunk.get("text", ""))

    # ==========================================================
    # DECISION SECTION
    # ==========================================================

    st.write("")
    st.divider()
    st.caption("AGENT 3 — DECISION AGENT")
    st.markdown("## 🛡️ Claim evaluation")
    st.write("")

    dec_val   = decision.get("decision", "—")
    dec_conf  = float(decision.get("confidence", 0))
    risk      = decision.get("risk_level", "—")
    guardrail = decision.get("guardrail_hit", "None")

    with st.container(border=True):
        col1, col2 = st.columns([1.4, 0.6], gap="large")
        with col1:
            st.caption("FINAL DECISION")
            if dec_val == "APPROVED":
                st.markdown("# 🟢 APPROVED")
                st.success("The claim satisfies the verification criteria.")
            else:
                st.markdown("# 🟠 HUMAN REVIEW")
                st.warning("The claim has been escalated for human verification.")
        with col2:
            st.caption("CONFIDENCE")
            st.markdown(f"# {dec_conf*100:.0f}%")
            st.progress(max(0.0, min(dec_conf, 1.0)))

    st.write("")

    col1, col2, col3 = st.columns(3)
    with col1: st.metric("DECISION", dec_val)
    with col2: st.metric("RISK", risk)
    with col3: st.metric("GUARDRAIL", guardrail)

    st.write("")

    with st.container(border=True):
        st.caption("DECISION REASON")
        st.write(decision.get("reason", "—"))

    evidence = decision.get("evidence_chain", [])
    if evidence:
        with st.container(border=True):
            st.caption("EVIDENCE CHAIN")
            for e in evidence:
                st.write(f"• {e}")

    with st.expander("View full reasoning steps"):
        st.write(decision.get("reasoning_steps", "—"))

    # ==========================================================
    # NAVIGATION
    # ==========================================================

    st.write("")
    st.divider()

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        if st.button("✓  View decision page", use_container_width=True, key="go_decision"):
            st.session_state.page = "Decision"
            st.rerun()

    st.write("")

    if st.button("↻  Run pipeline again", key="rerun_pipeline"):
        for key in ["vision_result", "rag_result", "decision_result", "order_info"]:
            st.session_state.pop(key, None)
        st.rerun()
