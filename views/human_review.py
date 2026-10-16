import streamlit as st
from io import BytesIO

from components.styles import apply_styles
from components.navbar import render_navbar, render_navigation


def show_human_review():

    apply_styles()
    render_navbar()
    render_navigation()

    st.write("")

    st.caption("HUMAN REVIEW  /  STEP 04")
    st.markdown("# Human verification center.")
    st.write(
        "Review the AI evidence and make the final decision "
        "when a claim requires human validation."
    )
    st.write("")

    # =========================================================
    # STEP INDICATOR
    # =========================================================

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.success("✓ Request")
    with col2: st.success("✓ AI Analysis")
    with col3: st.success("✓ Decision")
    with col4: st.warning("● Human Review")

    st.write("")

    # =========================================================
    # LOAD REAL DATA
    # =========================================================

    order_id       = st.session_state.get("order_id", "—")
    product_name   = st.session_state.get("product_name", "—")
    category       = st.session_state.get("product_category", "—")
    purchase_price = float(st.session_state.get("purchase_price", 0.0))
    description    = st.session_state.get("description", "—")
    image_bytes    = st.session_state.get("image_bytes")

    vision   = st.session_state.get("vision_result", {})
    rag      = st.session_state.get("rag_result", {})
    decision = st.session_state.get("decision_result", {})

    dec_conf  = float(decision.get("confidence", 0))
    guardrail = decision.get("guardrail_hit", "None")
    reason    = decision.get("reason", "—")

    # =========================================================
    # REVIEW STATUS
    # =========================================================

    with st.container(border=True):
        col1, col2, col3 = st.columns([1.5, 1, 1])
        with col1:
            st.caption("REVIEW STATUS")
            st.markdown("### 🟠 Awaiting human decision")
        with col2:
            st.caption("ORDER")
            st.markdown(f"### {order_id}")
        with col3:
            st.caption("AI CONFIDENCE")
            st.markdown(f"### {dec_conf*100:.0f}%")

    st.write("")

    # =========================================================
    # ESCALATION REASON
    # =========================================================

    if guardrail and guardrail != "None":
        with st.container(border=True):
            st.caption("ESCALATION REASON")
            st.warning(f"⚠ Guardrail triggered: **{guardrail}**")
            st.write(reason)

    st.write("")

    # =========================================================
    # PRODUCT EVIDENCE + ORDER INFO
    # =========================================================

    left, right = st.columns([1.05, 0.95], gap="large")

    with left:
        with st.container(border=True):
            st.caption("01  /  PRODUCT EVIDENCE")
            st.markdown("### 📸 Submitted image")

            if image_bytes:
                from PIL import Image
                image = Image.open(BytesIO(image_bytes)).convert("RGB")
                st.image(image, caption="Customer-provided evidence", use_container_width=True)
            else:
                st.info("No product image available.")

            st.write("")
            st.caption("CUSTOMER DESCRIPTION")
            st.info(description)

    with right:
        with st.container(border=True):
            st.caption("02  /  ORDER INFORMATION")
            st.markdown("### 📦 Claim details")
            st.write("")
            col1, col2 = st.columns(2)
            with col1:
                st.caption("ORDER ID")
                st.markdown(f"**{order_id}**")
            with col2:
                st.caption("CATEGORY")
                st.markdown(f"**{category}**")
            st.write("")
            col1, col2 = st.columns(2)
            with col1:
                st.caption("PRODUCT")
                st.markdown(f"**{product_name}**")
            with col2:
                st.caption("VALUE")
                st.markdown(f"**${purchase_price:.2f}**")
            st.write("")
            st.success("✓ Order information verified")

    # =========================================================
    # AI FINDINGS
    # =========================================================

    st.write("")
    st.divider()
    st.caption("03  /  AI FINDINGS")
    st.markdown("## What did the AI detect?")
    st.write("")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        with st.container(border=True):
            st.markdown("## 👁️")
            st.caption("PRODUCT")
            st.markdown(f"### {vision.get('product_type', '—')}")

    with col2:
        with st.container(border=True):
            st.markdown("## 💢")
            st.caption("DAMAGE")
            st.markdown(f"### {vision.get('damage_type', '—')[:30]}")

    with col3:
        with st.container(border=True):
            st.markdown("## 📍")
            st.caption("LOCATION")
            st.markdown(f"### {vision.get('damage_location', '—')[:30]}")

    with col4:
        with st.container(border=True):
            st.markdown("## ⚠️")
            st.caption("SEVERITY")
            st.markdown(f"### {vision.get('severity', '—')}")

    st.write("")

    with st.container(border=True):
        col1, col2 = st.columns([1.5, 0.5])
        with col1:
            st.caption("VISION AGENT")
            st.write(vision.get("description_consistency", "—"))
        with col2:
            st.metric("CONFIDENCE", f"{float(vision.get('confidence', 0))*100:.0f}%")

    # =========================================================
    # POLICY EVIDENCE
    # =========================================================

    st.write("")
    st.divider()
    st.caption("04  /  POLICY EVIDENCE")
    st.markdown("## 📚 Applicable return policy")
    st.write("")

    col1, col2 = st.columns([1.4, 0.6], gap="large")

    with col1:
        with st.container(border=True):
            st.caption("RETRIEVED KNOWLEDGE")
            st.markdown(f"### {rag.get('applicable_policy', '—')}")
            st.write(rag.get("summary", "—"))
            st.write("")
            st.success("✓ Policy retrieved from knowledge base")

    with col2:
        chunks = rag.get("chunks", [])
        top_score = max((c.get("relevance_score", 0) for c in chunks), default=0)
        with st.container(border=True):
            st.caption("TOP RELEVANCE")
            st.markdown(f"# {top_score:.2f}")
            st.progress(max(0.0, min(top_score / 10, 1.0)))
            st.caption("Reranker score")

    # =========================================================
    # AI RECOMMENDATION
    # =========================================================

    st.write("")
    st.divider()
    st.caption("05  /  AI RECOMMENDATION")
    st.markdown("## 🧠 Recommended action")
    st.write("")

    dec = decision.get("decision", "HUMAN_REVIEW")

    with st.container(border=True):
        col1, col2 = st.columns([1.4, 0.6], gap="large")
        with col1:
            if dec == "APPROVED":
                st.markdown("### 🟢 AI RECOMMENDS APPROVAL")
            else:
                st.markdown("### 🟠 AI RECOMMENDS HUMAN REVIEW")
            st.write(decision.get("reason", "—"))
        with col2:
            st.caption("AI CONFIDENCE")
            st.markdown(f"# {dec_conf*100:.0f}%")
            st.progress(max(0.0, min(dec_conf, 1.0)))

    # =========================================================
    # EVIDENCE CHAIN
    # =========================================================

    evidence = decision.get("evidence_chain", [])
    if evidence:
        st.write("")
        with st.container(border=True):
            st.caption("EVIDENCE CHAIN")
            for e in evidence:
                st.write(f"• {e}")

    # =========================================================
    # HUMAN DECISION
    # =========================================================

    st.write("")
    st.divider()
    st.caption("06  /  HUMAN DECISION")
    st.markdown("## Make the final decision")
    st.write(
        "The AI provides a recommendation, but the final "
        "decision remains under human control."
    )
    st.write("")

    human_dec = st.radio(
        "Decision",
        ["Approve return", "Reject return", "Request additional information"],
        horizontal=True,
        key="human_decision",
    )

    st.write("")

    comment = st.text_area(
        "Reviewer comments",
        placeholder="Add a note explaining your decision...",
        height=130,
    )

    st.write("")

    col1, col2, col3 = st.columns([1, 1.5, 1])

    with col2:
        if st.button("✓  Submit human decision", use_container_width=True, key="submit_human_decision"):
            st.session_state.review_completed = True
            st.session_state.review_result    = human_dec
            st.session_state.review_comment   = comment

            if human_dec == "Approve return":
                st.success("✓ Return approved by human reviewer.")
            elif human_dec == "Reject return":
                st.error("✕ Return rejected by human reviewer.")
            else:
                st.warning("ℹ Additional customer information requested.")

    # =========================================================
    # REVIEW COMPLETED
    # =========================================================

    if st.session_state.get("review_completed", False):
        st.write("")
        result          = st.session_state.get("review_result", "")
        reviewer_comment = st.session_state.get("review_comment", "")

        with st.container(border=True):
            st.caption("REVIEW COMPLETED")
            st.markdown("### ✓ Human decision recorded")
            st.write(f"Decision: **{result}**")
            if reviewer_comment:
                st.write(f"Reviewer comment: **{reviewer_comment}**")

    # =========================================================
    # AUDIT TRAIL
    # =========================================================

    st.write("")
    st.divider()
    st.caption("AUDIT TRAIL")
    st.markdown("## Decision traceability")
    st.write("")

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.success("✓ Customer evidence")
    with col2: st.success("✓ Vision analysis")
    with col3: st.success("✓ Policy retrieval")
    with col4: st.success("✓ Human validation")
