import streamlit as st

from components.styles import apply_styles
from components.navbar import (
    render_navbar,
    render_navigation
)


def show_human_review():

    apply_styles()

    render_navbar()
    render_navigation()

    st.write("")

    # =========================================================
    # PAGE HEADER
    # =========================================================

    st.caption(
        "HUMAN REVIEW  /  STEP 04"
    )

    st.markdown(
        "# Human verification center."
    )

    st.write(
        "Review the AI evidence and make the final decision "
        "when a claim requires human validation."
    )

    st.write("")

    # =========================================================
    # STATUS
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
        st.warning("● Human Review")

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

    category = st.session_state.get(
        "product_category",
        "Footwear"
    )

    purchase_price = st.session_state.get(
        "purchase_price",
        120.0
    )

    description = st.session_state.get(
        "description",
        "The shoes arrived with a stain on the left shoe."
    )

    uploaded_image = st.session_state.get(
        "uploaded_image",
        None
    )

    # =========================================================
    # REVIEW STATUS
    # =========================================================

    with st.container(border=True):

        col1, col2, col3 = st.columns(
            [1.5, 1, 1]
        )

        with col1:

            st.caption(
                "REVIEW STATUS"
            )

            st.markdown(
                "### 🟠 Awaiting human decision"
            )

        with col2:

            st.caption(
                "ORDER"
            )

            st.markdown(
                f"### {order_id}"
            )

        with col3:

            st.caption(
                "AI CONFIDENCE"
            )

            st.markdown(
                "### 89%"
            )

    st.write("")

    # =========================================================
    # MAIN REVIEW AREA
    # =========================================================

    left, right = st.columns(
        [1.05, 0.95],
        gap="large"
    )

    # =========================================================
    # LEFT — PRODUCT EVIDENCE
    # =========================================================

    with left:

        with st.container(border=True):

            st.caption(
                "01  /  PRODUCT EVIDENCE"
            )

            st.markdown(
                "### 📸 Submitted image"
            )

            if uploaded_image:

                st.image(
                    uploaded_image,
                    caption="Customer-provided evidence",
                    use_container_width=True
                )

            else:

                st.info(
                    "No product image available."
                )

            st.write("")

            st.caption(
                "CUSTOMER DESCRIPTION"
            )

            st.info(
                description
            )

    # =========================================================
    # RIGHT — ORDER INFORMATION
    # =========================================================

    with right:

        with st.container(border=True):

            st.caption(
                "02  /  ORDER INFORMATION"
            )

            st.markdown(
                "### 📦 Claim details"
            )

            st.write("")

            col1, col2 = st.columns(
                2
            )

            with col1:

                st.caption(
                    "ORDER ID"
                )

                st.markdown(
                    f"**{order_id}**"
                )

            with col2:

                st.caption(
                    "CATEGORY"
                )

                st.markdown(
                    f"**{category}**"
                )

            st.write("")

            col1, col2 = st.columns(
                2
            )

            with col1:

                st.caption(
                    "PRODUCT"
                )

                st.markdown(
                    f"**{product_name}**"
                )

            with col2:

                st.caption(
                    "VALUE"
                )

                st.markdown(
                    f"**${purchase_price:.2f}**"
                )

            st.write("")

            st.success(
                "✓ Order information verified"
            )

    # =========================================================
    # AI FINDINGS
    # =========================================================

    st.write("")
    st.divider()

    st.caption(
        "03  /  AI FINDINGS"
    )

    st.markdown(
        "## What did the AI detect?"
    )

    st.write("")

    col1, col2, col3, col4 = st.columns(
        4
    )

    with col1:

        with st.container(border=True):

            st.markdown(
                "## 👟"
            )

            st.caption(
                "PRODUCT"
            )

            st.markdown(
                "### Running shoes"
            )

    with col2:

        with st.container(border=True):

            st.markdown(
                "## 💧"
            )

            st.caption(
                "DAMAGE"
            )

            st.markdown(
                "### Stain"
            )

    with col3:

        with st.container(border=True):

            st.markdown(
                "## 📍"
            )

            st.caption(
                "LOCATION"
            )

            st.markdown(
                "### Left shoe"
            )

    with col4:

        with st.container(border=True):

            st.markdown(
                "## ⚠️"
            )

            st.caption(
                "SEVERITY"
            )

            st.markdown(
                "### Medium"
            )

    st.write("")

    with st.container(border=True):

        col1, col2 = st.columns(
            [1.5, 0.5]
        )

        with col1:

            st.caption(
                "VISION AGENT"
            )

            st.markdown(
                "Visual evidence is consistent with "
                "the customer's reported issue."
            )

        with col2:

            st.metric(
                "CONFIDENCE",
                "91%"
            )

    # =========================================================
    # POLICY EVIDENCE
    # =========================================================

    st.write("")
    st.divider()

    st.caption(
        "04  /  POLICY EVIDENCE"
    )

    st.markdown(
        "## 📚 Applicable return policy"
    )

    st.write("")

    col1, col2 = st.columns(
        [1.4, 0.6],
        gap="large"
    )

    with col1:

        with st.container(border=True):

            st.caption(
                "RETRIEVED KNOWLEDGE"
            )

            st.markdown(
                "### Return & Refund Policy"
            )

            st.write(
                """
                Products received with visible defects or
                damage may qualify for a return or refund
                when the issue is reported within the
                applicable return period.
                """
            )

            st.write("")

            st.success(
                "✓ Policy supports the claim"
            )

    with col2:

        with st.container(border=True):

            st.caption(
                "RAG SCORE"
            )

            st.markdown(
                "# 94%"
            )

            st.progress(
                0.94
            )

            st.caption(
                "Policy relevance"
            )

    # =========================================================
    # AI RECOMMENDATION
    # =========================================================

    st.write("")
    st.divider()

    st.caption(
        "05  /  AI RECOMMENDATION"
    )

    st.markdown(
        "## 🧠 Recommended action"
    )

    st.write("")

    with st.container(border=True):

        col1, col2 = st.columns(
            [1.4, 0.6],
            gap="large"
        )

        with col1:

            st.markdown(
                "### 🟢 APPROVE RETURN"
            )

            st.write(
                """
                The AI recommends approving the return because
                the visual evidence supports the customer's
                claim and the retrieved policy allows returns
                for products received with visible damage.
                """
            )

        with col2:

            st.caption(
                "AI CONFIDENCE"
            )

            st.markdown(
                "# 89%"
            )

            st.progress(
                0.89
            )

    # =========================================================
    # HUMAN DECISION
    # =========================================================

    st.write("")
    st.divider()

    st.caption(
        "06  /  HUMAN DECISION"
    )

    st.markdown(
        "## Make the final decision"
    )

    st.write(
        "The AI provides a recommendation, but the final "
        "decision remains under human control."
    )

    st.write("")

    decision = st.radio(
        "Decision",
        [
            "Approve return",
            "Reject return",
            "Request additional information"
        ],
        horizontal=True,
        key="human_decision"
    )

    st.write("")

    comment = st.text_area(
        "Reviewer comments",
        placeholder=(
            "Add a note explaining your decision..."
        ),
        height=130
    )

    st.write("")

    # =========================================================
    # FINAL ACTION
    # =========================================================

    col1, col2, col3 = st.columns(
        [1, 1.5, 1]
    )

    with col2:

        if st.button(
            "✓  Submit human decision",
            use_container_width=True,
            key="submit_human_decision"
        ):

            st.session_state.review_completed = True
            st.session_state.review_result = decision
            st.session_state.review_comment = comment

            if decision == "Approve return":

                st.success(
                    "✓ Return approved by human reviewer."
                )

            elif decision == "Reject return":

                st.error(
                    "✕ Return rejected by human reviewer."
                )

            else:

                st.warning(
                    "ℹ Additional customer information requested."
                )

    # =========================================================
    # REVIEW COMPLETED
    # =========================================================

    if st.session_state.get(
        "review_completed",
        False
    ):

        st.write("")

        result = st.session_state.get(
            "review_result",
            ""
        )

        reviewer_comment = st.session_state.get(
            "review_comment",
            ""
        )

        with st.container(border=True):

            st.caption(
                "REVIEW COMPLETED"
            )

            st.markdown(
                "### ✓ Human decision recorded"
            )

            st.write(
                f"Decision: **{result}**"
            )

            if reviewer_comment:

                st.write(
                    f"Reviewer comment: **{reviewer_comment}**"
                )

    # =========================================================
    # TRACEABILITY
    # =========================================================

    st.write("")
    st.divider()

    st.caption(
        "AUDIT TRAIL"
    )

    st.markdown(
        "## Decision traceability"
    )

    st.write("")

    col1, col2, col3, col4 = st.columns(
        4
    )

    with col1:

        st.success(
            "✓ Customer evidence"
        )

    with col2:

        st.success(
            "✓ Vision analysis"
        )

    with col3:

        st.success(
            "✓ Policy retrieval"
        )

    with col4:

        st.success(
            "✓ Human validation"
        )