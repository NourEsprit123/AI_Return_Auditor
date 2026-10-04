import streamlit as st

from components.styles import apply_styles
from components.navbar import (
    render_navbar,
    render_navigation
)


def show_decision():

    apply_styles()

    render_navbar()
    render_navigation()

    st.write("")

    # =========================================================
    # PAGE HEADER
    # =========================================================

    st.caption(
        "DECISION  /  STEP 03"
    )

    st.markdown(
        "# Your claim has been evaluated."
    )

    st.write(
        "The AI system combined visual evidence, retrieved "
        "policy and decision guardrails to evaluate the claim."
    )

    st.write("")

    # =========================================================
    # CLAIM DATA
    # =========================================================

    order_id = st.session_state.get(
        "order_id",
        "45872"
    )

    product_name = st.session_state.get(
        "product_name",
        "Nike Pegasus 41"
    )

    purchase_price = st.session_state.get(
        "purchase_price",
        120.0
    )

    # =========================================================
    # STEP INDICATOR
    # =========================================================

    col1, col2, col3, col4 = st.columns(
        4
    )

    with col1:
        st.success("✓ Request")

    with col2:
        st.success("✓ AI Analysis")

    with col3:
        st.success("✓ Decision")

    with col4:
        st.caption("○ Human Review")

    st.write("")

    # =========================================================
    # MAIN DECISION
    # =========================================================

    with st.container(border=True):

        col1, col2 = st.columns(
            [1.4, 0.6],
            gap="large"
        )

        with col1:

            st.caption(
                "FINAL AI DECISION"
            )

            st.markdown(
                "# 🟢 RETURN APPROVED"
            )

            st.write(
                "The available evidence and applicable policy "
                "support the customer's return request."
            )

            st.write("")

            st.success(
                "✓ The claim satisfies the current verification criteria."
            )

        with col2:

            st.caption(
                "CONFIDENCE"
            )

            st.markdown(
                "# 89%"
            )

            st.progress(
                0.89
            )

            st.caption(
                "Overall decision confidence"
            )

    st.write("")

    # =========================================================
    # DECISION METRICS
    # =========================================================

    col1, col2, col3, col4 = st.columns(
        4
    )

    with col1:

        st.metric(
            "DECISION",
            "APPROVED"
        )

    with col2:

        st.metric(
            "CONFIDENCE",
            "89%"
        )

    with col3:

        st.metric(
            "ORDER VALUE",
            f"${purchase_price:.2f}"
        )

    with col4:

        st.metric(
            "RISK",
            "LOW"
        )

    # =========================================================
    # DECISION REASONS
    # =========================================================

    st.write("")
    st.divider()

    st.caption(
        "DECISION EXPLANATION"
    )

    st.markdown(
        "## Why was the claim approved?"
    )

    st.write("")

    col1, col2 = st.columns(
        2,
        gap="large"
    )

    with col1:

        with st.container(border=True):

            st.caption(
                "01  /  VISUAL EVIDENCE"
            )

            st.markdown(
                "### 👁️ Damage confirmed"
            )

            st.write(
                """
                The Vision Agent identified a visible stain
                on the left shoe. The detected damage is
                consistent with the customer's description.
                """
            )

            st.write("")

            st.success(
                "91% visual confidence"
            )

    with col2:

        with st.container(border=True):

            st.caption(
                "02  /  POLICY EVIDENCE"
            )

            st.markdown(
                "### 📚 Return policy applies"
            )

            st.write(
                """
                The retrieved policy indicates that products
                received with visible defects or damage may
                qualify for return within the applicable period.
                """
            )

            st.write("")

            st.success(
                "94% policy relevance"
            )

    # =========================================================
    # GUARDRAILS
    # =========================================================

    st.write("")

    with st.container(border=True):

        st.caption(
            "03  /  SAFETY GUARDRAILS"
        )

        st.markdown(
            "### 🛡️ Verification checks"
        )

        st.write(
            "Before producing the final decision, "
            "the system verified the following conditions."
        )

        st.write("")

        checks = [
            "Visual evidence is available",
            "Customer description is consistent",
            "Relevant policy was retrieved",
            "Claim does not exceed the defined risk threshold",
            "No immediate escalation condition detected"
        ]

        for check in checks:

            st.success(
                f"✓ {check}"
            )

    # =========================================================
    # EVIDENCE CHAIN
    # =========================================================

    st.write("")
    st.divider()

    st.caption(
        "DECISION TRACEABILITY"
    )

    st.markdown(
        "## Evidence used by the system"
    )

    st.write("")

    col1, col2, col3 = st.columns(
        3,
        gap="large"
    )

    with col1:

        with st.container(border=True):

            st.markdown(
                "## 👁️"
            )

            st.caption(
                "VISION AGENT"
            )

            st.markdown(
                "Damage detected"
            )

            st.write(
                "Stain · Left shoe · Medium"
            )

            st.metric(
                "Confidence",
                "91%"
            )

    with col2:

        with st.container(border=True):

            st.markdown(
                "## 📚"
            )

            st.caption(
                "RAG AGENT"
            )

            st.markdown(
                "Policy retrieved"
            )

            st.write(
                "Return & Refund Policy"
            )

            st.metric(
                "Relevance",
                "94%"
            )

    with col3:

        with st.container(border=True):

            st.markdown(
                "## 🛡️"
            )

            st.caption(
                "GUARDRAILS"
            )

            st.markdown(
                "Risk evaluation"
            )

            st.write(
                "Low risk · No escalation"
            )

            st.metric(
                "Score",
                "89%"
            )

    # =========================================================
    # ORDER SUMMARY
    # =========================================================

    st.write("")
    st.divider()

    st.caption(
        "CLAIM SUMMARY"
    )

    st.markdown(
        "## Return request details"
    )

    st.write("")

    with st.container(border=True):

        col1, col2, col3 = st.columns(
            3
        )

        with col1:

            st.caption(
                "ORDER ID"
            )

            st.markdown(
                f"### {order_id}"
            )

        with col2:

            st.caption(
                "PRODUCT"
            )

            st.markdown(
                f"### {product_name}"
            )

        with col3:

            st.caption(
                "REFUND VALUE"
            )

            st.markdown(
                f"### ${purchase_price:.2f}"
            )

    # =========================================================
    # FINAL ACTION
    # =========================================================

    st.write("")
    st.divider()

    with st.container(border=True):

        st.caption(
            "NEXT STEP"
        )

        st.markdown(
            "### What would you like to do?"
        )

        st.write(
            "The claim has been automatically approved. "
            "You can finalize the process or send it "
            "to a human reviewer for additional verification."
        )

        st.write("")

        col1, col2 = st.columns(
            2,
            gap="large"
        )

        with col1:

            if st.button(
                "✓  Confirm approval",
                use_container_width=True,
                key="confirm_approval"
            ):

                st.session_state.decision_confirmed = True

                st.success(
                    "Return approval confirmed."
                )

        with col2:

            if st.button(
                "🧑‍💼  Send to human review",
                use_container_width=True,
                key="send_human_review"
            ):

                st.session_state.page = (
                    "Human Review"
                )

                st.rerun()

    # =========================================================
    # CONFIRMATION
    # =========================================================

    if st.session_state.get(
        "decision_confirmed",
        False
    ):

        st.write("")

        st.success(
            "✓ The return approval has been confirmed successfully."
        )

        st.info(
            "The claim can now proceed to the final "
            "customer-service workflow."
        )