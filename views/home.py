import streamlit as st

from components.styles import apply_styles
from components.navbar import (
    render_navbar,
    render_navigation
)
from components.cards import render_feature_card


def show_home():

    apply_styles()

    render_navbar()
    render_navigation()

    st.write("")

    # =========================================================
    # HERO SECTION
    # =========================================================

    hero_left, hero_right = st.columns(
        [1.35, 0.85],
        gap="large"
    )

    with hero_left:

        st.caption(
            "✦  AI-POWERED RETURN VERIFICATION"
        )

        st.markdown(
            "# Return with confidence."
        )

        st.markdown(
            "## Let intelligent agents verify your claim."
        )

        st.write(
            """
            AI Return Auditor combines computer vision,
            Retrieval-Augmented Generation and decision
            guardrails to analyze e-commerce return claims
            quickly and transparently.
            """
        )

        st.write("")

        col1, col2 = st.columns(
            [1, 1],
            gap="medium"
        )

        with col1:

            if st.button(
                "🚀  Start a return",
                use_container_width=True,
                key="home_start_return"
            ):

                st.session_state.page = "Return Request"
                st.rerun()

        with col2:

            if st.button(
                "◈  Explore AI analysis",
                use_container_width=True,
                key="home_explore_ai"
            ):

                st.session_state.page = "AI Analysis"
                st.rerun()

        st.write("")

        st.caption(
            "✓ Multimodal AI   •   ✓ Policy RAG   •   ✓ Human-in-the-loop"
        )

    # =========================================================
    # HERO RIGHT — AI STATUS CARD
    # =========================================================

    with hero_right:

        with st.container(border=True):

            st.caption(
                "AI VERIFICATION ENGINE"
            )

            st.markdown(
                "### Claim Intelligence"
            )

            st.write(
                "Three specialized components "
                "work together to evaluate every claim."
            )

            st.write("")

            # Agent 1
            col1, col2 = st.columns(
                [0.7, 3.3]
            )

            with col1:
                st.markdown("## 👁️")

            with col2:
                st.markdown("**Vision Agent**")
                st.caption("Multimodal damage analysis")

            st.divider()

            # Agent 2
            col1, col2 = st.columns(
                [0.7, 3.3]
            )

            with col1:
                st.markdown("## 📚")

            with col2:
                st.markdown("**Policy RAG**")
                st.caption("Relevant policy retrieval")

            st.divider()

            # Agent 3
            col1, col2 = st.columns(
                [0.7, 3.3]
            )

            with col1:
                st.markdown("## 🛡️")

            with col2:
                st.markdown("**Decision Guardrails**")
                st.caption("Safe approval or escalation")

            st.write("")

            st.success(
                "✓ Human review available when required"
            )

    # =========================================================
    # SYSTEM METRICS
    # =========================================================

    st.write("")
    st.divider()

    st.caption(
        "SYSTEM OVERVIEW"
    )

    st.markdown(
        "## Intelligent return verification"
    )

    st.write(
        "A complete AI workflow from customer evidence "
        "to a transparent decision."
    )

    st.write("")

    col1, col2, col3, col4 = st.columns(
        4,
        gap="medium"
    )

    with col1:

        st.metric(
            "AI COMPONENTS",
            "03",
            "Specialized"
        )

    with col2:

        st.metric(
            "INPUT",
            "IMAGE + TEXT",
            "Multimodal"
        )

    with col3:

        st.metric(
            "KNOWLEDGE",
            "RAG",
            "Policy-aware"
        )

    with col4:

        st.metric(
            "ESCALATION",
            "HUMAN",
            "When needed"
        )

    # =========================================================
    # WORKFLOW
    # =========================================================

    st.write("")
    st.divider()

    st.caption(
        "HOW IT WORKS"
    )

    st.markdown(
        "## From evidence to decision"
    )

    st.write(
        "Every claim follows the same transparent verification pipeline."
    )

    st.write("")

    col1, col2, col3, col4 = st.columns(
        4,
        gap="medium"
    )

    with col1:

        with st.container(border=True):

            st.markdown("## 01")

            st.markdown(
                "### 📦 Claim"
            )

            st.write(
                "Customer submits the product image, "
                "description and order information."
            )

    with col2:

        with st.container(border=True):

            st.markdown("## 02")

            st.markdown(
                "### 👁️ Vision"
            )

            st.write(
                "AI analyzes the image and identifies "
                "damage, location and severity."
            )

    with col3:

        with st.container(border=True):

            st.markdown("## 03")

            st.markdown(
                "### 📚 Policy"
            )

            st.write(
                "RAG retrieves the most relevant "
                "return and refund rules."
            )

    with col4:

        with st.container(border=True):

            st.markdown("## 04")

            st.markdown(
                "### 🛡️ Decision"
            )

            st.write(
                "Guardrails combine evidence and "
                "policy before approving or escalating."
            )

    # =========================================================
    # AI AGENTS
    # =========================================================

    st.write("")
    st.divider()

    st.caption(
        "AI ARCHITECTURE"
    )

    st.markdown(
        "## Three specialized AI agents"
    )

    st.write(
        "Each component has one clear responsibility."
    )

    st.write("")

    col1, col2, col3 = st.columns(
        3,
        gap="large"
    )

    with col1:

        render_feature_card(
            "👁️",
            "AGENT 01",
            "Multimodal Vision",
            "Analyzes product images and customer "
            "descriptions to identify the product, "
            "damage type, location, severity and "
            "confidence."
        )

    with col2:

        render_feature_card(
            "📚",
            "AGENT 02",
            "Policy RAG",
            "Retrieves relevant return, refund and "
            "warranty policies from the project's "
            "knowledge base."
        )

    with col3:

        render_feature_card(
            "🛡️",
            "AGENT 03",
            "Claim Evaluator",
            "Combines order information, visual "
            "evidence and retrieved policies to "
            "produce a safe decision."
        )

    # =========================================================
    # TRANSPARENCY SECTION
    # =========================================================

    st.write("")
    st.divider()

    left, right = st.columns(
        [1.2, 0.8],
        gap="large"
    )

    with left:

        st.caption(
            "DESIGNED FOR TRUST"
        )

        st.markdown(
            "## AI decisions should be explainable."
        )

        st.write(
            """
            AI Return Auditor does not simply return
            an approval or rejection. The system keeps
            the evidence, retrieved policy and reasoning
            behind the decision visible to the reviewer.
            """
        )

        st.write("")

        st.info(
            "🔎 Evidence-based analysis"
        )

        st.info(
            "📚 Policy-grounded decisions"
        )

        st.info(
            "🧑‍💼 Human escalation when uncertain"
        )

    with right:

        with st.container(border=True):

            st.caption(
                "DECISION PRINCIPLE"
            )

            st.markdown(
                "### Evidence + Knowledge"
            )

            st.markdown(
                "## ↓"
            )

            st.markdown(
                "### Safe Decision"
            )

            st.write("")

            st.success(
                "APPROVED"
            )

            st.warning(
                "or HUMAN REVIEW"
            )

    # =========================================================
    # FINAL CTA
    # =========================================================

    st.write("")
    st.divider()

    with st.container(border=True):

        col1, col2 = st.columns(
            [3, 1],
            gap="large"
        )

        with col1:

            st.caption(
                "READY TO TEST THE AUDITOR?"
            )

            st.markdown(
                "### Submit a return claim and let AI investigate it."
            )

            st.write(
                "Upload your evidence and follow the complete "
                "verification pipeline."
            )

        with col2:

            if st.button(
                "🚀 Start now",
                use_container_width=True,
                key="home_final_start"
            ):

                st.session_state.page = "Return Request"
                st.rerun()