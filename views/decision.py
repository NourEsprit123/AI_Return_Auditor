import streamlit as st

from components.styles import apply_styles
from components.navbar import render_navbar, render_navigation


def show_decision():

    apply_styles()
    render_navbar()
    render_navigation()

    st.write("")

    st.caption("DECISION  /  STEP 03")
    st.markdown("# Your claim has been evaluated.")
    st.write(
        "The AI system combined visual evidence, retrieved "
        "policy and decision guardrails to evaluate the claim."
    )
    st.write("")

    # =========================================================
    # LOAD REAL DATA FROM SESSION STATE
    # =========================================================

    order_id       = st.session_state.get("order_id", "—")
    product_name   = st.session_state.get("product_name", "—")
    purchase_price = float(st.session_state.get("purchase_price", 0.0))

    vision   = st.session_state.get("vision_result", {})
    rag      = st.session_state.get("rag_result", {})
    decision = st.session_state.get("decision_result", {})

    # Check if pipeline has been run
    pipeline_done = bool(vision and rag and decision)

    # =========================================================
    # STEP INDICATOR
    # =========================================================

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.success("✓ Request")
    with col2: st.success("✓ AI Analysis")
    with col3: st.success("✓ Decision")
    with col4: st.caption("○ Human Review")

    st.write("")

    # =========================================================
    # NO PIPELINE RUN YET
    # =========================================================

    if not pipeline_done:
        st.warning(
            "⚠️ No AI analysis has been run yet. "
            "Please go to AI Analysis first."
        )
        if st.button("← Go to AI Analysis", key="go_analysis"):
            st.session_state.page = "AI Analysis"
            st.rerun()
        return

    # =========================================================
    # EXTRACT DECISION DATA
    # =========================================================

    dec       = decision.get("decision", "HUMAN_REVIEW")
    dec_conf  = float(decision.get("confidence", 0))
    risk      = decision.get("risk_level", "MEDIUM")
    reason    = decision.get("reason", "—")
    guardrail = decision.get("guardrail_hit", "None")
    evidence  = decision.get("evidence_chain", [])

    vision_conf     = float(vision.get("confidence", 0))
    applicable_pol  = rag.get("applicable_policy", "—")
    policy_summary  = rag.get("summary", "—")

    # =========================================================
    # MAIN DECISION CARD
    # =========================================================

    with st.container(border=True):
        col1, col2 = st.columns([1.4, 0.6], gap="large")

        with col1:
            st.caption("FINAL AI DECISION")

            if dec == "APPROVED":
                st.markdown("# 🟢 RETURN APPROVED")
                st.write("The available evidence and applicable policy support the return request.")
                st.write("")
                st.success("✓ The claim satisfies all verification criteria.")
            else:
                st.markdown("# 🟠 HUMAN REVIEW REQUIRED")
                st.write("The claim has been escalated for manual verification.")
                st.write("")
                st.warning(f"⚠ Reason: {reason}")

        with col2:
            st.caption("CONFIDENCE")
            st.markdown(f"# {dec_conf*100:.0f}%")
            st.progress(max(0.0, min(dec_conf, 1.0)))
            st.caption("Overall decision confidence")

    st.write("")

    # =========================================================
    # METRICS
    # =========================================================

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("DECISION", dec)
    with col2: st.metric("CONFIDENCE", f"{dec_conf*100:.0f}%")
    with col3: st.metric("ORDER VALUE", f"${purchase_price:.2f}")
    with col4: st.metric("RISK", risk)

    # =========================================================
    # DECISION EXPLANATION
    # =========================================================

    st.write("")
    st.divider()
    st.caption("DECISION EXPLANATION")

    if dec == "APPROVED":
        st.markdown("## Why was the claim approved?")
    else:
        st.markdown("## Why was the claim escalated?")

    st.write("")

    col1, col2 = st.columns(2, gap="large")

    with col1:
        with st.container(border=True):
            st.caption("01  /  VISUAL EVIDENCE")
            st.markdown("### 👁️ Vision Agent")
            st.write(vision.get("visual_evidence", "—"))
            st.write("")
            sev = vision.get("severity", "Unknown")
            consistency = vision.get("description_consistency", "")
            if "inconsistent" in consistency.lower():
                st.warning(f"⚠ {sev} severity — Inconsistent description")
            else:
                st.success(f"✓ {sev} severity — {vision_conf*100:.0f}% confidence")

    with col2:
        with st.container(border=True):
            st.caption("02  /  POLICY EVIDENCE")
            st.markdown("### 📚 RAG Agent")
            st.write(policy_summary[:300] + "..." if len(policy_summary) > 300 else policy_summary)
            st.write("")
            st.success(f"✓ {applicable_pol}")

    # =========================================================
    # GUARDRAILS
    # =========================================================

    st.write("")

    with st.container(border=True):
        st.caption("03  /  SAFETY GUARDRAILS")
        st.markdown("### 🛡️ Verification checks")
        st.write("")

        if guardrail == "None" or not guardrail:
            checks = [
                "Visual evidence is available",
                "Customer description is consistent",
                "Relevant policy was retrieved",
                "Claim within risk threshold",
                "No escalation condition detected",
            ]
            for check in checks:
                st.success(f"✓ {check}")
        else:
            st.warning(f"⚠ Guardrail triggered: **{guardrail}**")
            st.write(reason)

    # =========================================================
    # EVIDENCE CHAIN
    # =========================================================

    st.write("")
    st.divider()
    st.caption("DECISION TRACEABILITY")
    st.markdown("## Evidence used by the system")
    st.write("")

    col1, col2, col3 = st.columns(3, gap="large")

    with col1:
        with st.container(border=True):
            st.markdown("## 👁️")
            st.caption("VISION AGENT")
            st.markdown(f"**{vision.get('product_type', '—')}**")
            st.write(f"{vision.get('damage_type', '—')} · {vision.get('severity', '—')}")
            st.metric("Confidence", f"{vision_conf*100:.0f}%")

    with col2:
        with st.container(border=True):
            st.markdown("## 📚")
            st.caption("RAG AGENT")
            st.markdown(f"**{applicable_pol}**")
            sources = rag.get("sources", [])
            st.write(", ".join(sources) if sources else "—")
            chunks = rag.get("chunks", [])
            top_score = max((c.get("relevance_score", 0) for c in chunks), default=0)
            st.metric("Top Relevance", f"{top_score:.2f}")

    with col3:
        with st.container(border=True):
            st.markdown("## 🛡️")
            st.caption("GUARDRAILS")
            st.markdown(f"**{risk} risk**")
            st.write(f"Guardrail: {guardrail}")
            st.metric("Decision Score", f"{dec_conf*100:.0f}%")

    # =========================================================
    # EVIDENCE CHAIN LIST
    # =========================================================

    if evidence:
        st.write("")
        with st.container(border=True):
            st.caption("FULL EVIDENCE CHAIN")
            for e in evidence:
                st.write(f"• {e}")

    # =========================================================
    # CLAIM SUMMARY
    # =========================================================

    st.write("")
    st.divider()
    st.caption("CLAIM SUMMARY")
    st.markdown("## Return request details")
    st.write("")

    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.caption("ORDER ID")
            st.markdown(f"### {order_id}")
        with col2:
            st.caption("PRODUCT")
            st.markdown(f"### {product_name}")
        with col3:
            st.caption("REFUND VALUE")
            st.markdown(f"### ${purchase_price:.2f}")

    # =========================================================
    # FINAL ACTION
    # =========================================================

    st.write("")
    st.divider()

    with st.container(border=True):
        st.caption("NEXT STEP")

        if dec == "APPROVED":
            st.markdown("### What would you like to do?")
            st.write("The claim has been automatically approved. You can confirm or send to human review.")
            st.write("")
            col1, col2 = st.columns(2, gap="large")
            with col1:
                if st.button("✓  Confirm approval", use_container_width=True, key="confirm_approval"):
                    st.session_state.decision_confirmed = True
                    st.success("Return approval confirmed.")
            with col2:
                if st.button("🧑‍💼  Send to human review", use_container_width=True, key="send_human_review"):
                    st.session_state.page = "Human Review"
                    st.rerun()
        else:
            st.markdown("### This claim requires human review.")
            st.write("The AI detected an issue that requires manual verification.")
            st.write("")
            if st.button("🧑‍💼  Go to human review", use_container_width=True, key="go_human_review"):
                st.session_state.page = "Human Review"
                st.rerun()

    if st.session_state.get("decision_confirmed", False):
        st.write("")
        st.success("✓ The return approval has been confirmed successfully.")
        st.info("The claim can now proceed to the final customer-service workflow.")
