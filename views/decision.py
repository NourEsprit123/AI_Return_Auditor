
import streamlit as st

from components.styles import apply_styles
from components.navbar import (
    render_navbar,
    render_navigation,
)

from agents.rag_agent import RAGAgent
from agents.decision_agent import DecisionAgent
import streamlit as st

from components.styles import apply_styles
from components.navbar import (
    render_navbar,
    render_navigation,
)




# =========================================================
# SESSION HELPERS
# =========================================================

def _get_vision_result():
    """Récupère le résultat du Vision Agent depuis la session."""

    possible_keys = (
        "vision_result",
        "vision_analysis",
        "analysis_result",
        "ai_analysis_result",
        "vision_output",
    )

    for key in possible_keys:
        value = st.session_state.get(key)

        if isinstance(value, dict) and value:
            if isinstance(value.get("result"), dict):
                return value["result"]

            return value

    return {}


def _get_decision_result(claim, order_id):
    """
    Exécute le pipeline RAG + Decision Agent une seule fois
    par réclamation, sauf si l'utilisateur relance l'analyse.
    """

    cache_key = f"decision_result_{order_id}"

    if cache_key in st.session_state:
        return st.session_state[cache_key]

    with st.spinner(
        "Searching approved policies and evaluating the claim..."
    ):
        rag_agent = RAGAgent()
        rag_result = rag_agent.run(claim)

        if not isinstance(rag_result, dict):
            raise ValueError(
                "The RAG Agent did not return a valid dictionary."
            )

        decision_agent = DecisionAgent()

        decision_result = decision_agent.evaluate(
            claim,
            rag_result,
        )

        if not isinstance(decision_result, dict):
            raise ValueError(
                "The Decision Agent did not return a valid dictionary."
            )

        # Conserver le résultat RAG pour la traçabilité.
        decision_result.setdefault("rag_result", rag_result)

        # Préserver les sources et citations du RAG si le
        # Decision Agent ne les a pas déjà transmises.
        decision_result.setdefault(
            "sources",
            rag_result.get("sources", []),
        )

        decision_result.setdefault(
            "citations",
            rag_result.get("citations", []),
        )

        decision_result.setdefault(
            "missing_information",
            rag_result.get("missing_information", []),
        )

        decision_result.setdefault(
            "needs_human_review",
            rag_result.get("needs_human_review", True),
        )

        st.session_state[cache_key] = decision_result

    return st.session_state[cache_key]


# =========================================================
# DISPLAY HELPERS
# =========================================================

def _display_value(value):
    """Convertit une valeur en texte lisible dans Streamlit."""

    if value is None or value == "":
        return "Not specified"

    if isinstance(value, (dict, list)):
        return str(value)

    return str(value)


def _display_list(items, empty_message):
    """Affiche une liste de résultats."""

    if not isinstance(items, list) or not items:
        st.info(empty_message)
        return

    for item in items:
        if isinstance(item, dict):
            st.write(
                "- "
                + _display_value(
                    item.get("text", item.get("description", item))
                )
            )
        else:
            st.write(f"- {_display_value(item)}")


def _normalize_confidence(value):
    """Normalise une confiance entre 0 et 1."""

    if not isinstance(value, (int, float)):
        return None

    if value > 1:
        value = value / 100

    return max(0.0, min(1.0, value))


# =========================================================
# MAIN PAGE
# =========================================================

def show_decision():

    apply_styles()
    render_navbar()
    render_navigation()

    st.write("")

    # =====================================================
    # PAGE HEADER
    # =====================================================

    st.caption("DECISION / STEP 03")
    st.title("Return claim assessment")

    st.write(
        "The system retrieves relevant policy passages, "
        "analyses visual evidence and prepares a preliminary "
        "assessment. Human verification remains necessary "
        "when evidence or policy information is insufficient."
    )

    # =====================================================
    # CLAIM DATA
    # =====================================================

    order_id = st.session_state.get("order_id", "45872")

    product_name = st.session_state.get(
        "product_name",
        "Unknown product",
    )

    purchase_price = st.session_state.get(
        "purchase_price",
        0.0,
    )

    try:
        purchase_price = float(purchase_price or 0.0)
    except (TypeError, ValueError):
        purchase_price = 0.0

    description = st.session_state.get("description", "")
    vision_result = _get_vision_result()

    claim = {
        "order_id": str(order_id),
        "product_name": product_name,
        "product_category": st.session_state.get(
            "product_category",
            "",
        ),
        "purchase_price": purchase_price,
        "quantity": st.session_state.get("quantity", 1),
        "customer_name": st.session_state.get(
            "customer_name",
            "",
        ),
        "company_name": st.session_state.get(
            "company_name",
            "",
        ),
        "description": description,
        "delivery_date": st.session_state.get(
            "delivery_date",
            "",
        ),
        "order_date": st.session_state.get(
            "order_date",
            "",
        ),
        "delivery_status": st.session_state.get(
            "delivery_status",
            "",
        ),
        "vision": vision_result,
    }

    # =====================================================
    # STEP INDICATOR
    # =====================================================

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.success("✓ Request")

    with col2:
        st.success("✓ AI Analysis")

    with col3:
        st.info("● Decision")

    with col4:
        st.caption("○ Human Review")

    st.divider()

    # =====================================================
    # RE-RUN CONTROL
    # =====================================================

    if st.button(
        "Re-run policy assessment",
        key="rerun_policy_assessment",
    ):
        st.session_state.pop(
            f"decision_result_{order_id}",
            None,
        )
        st.rerun()

    # =====================================================
    # RUN RAG + DECISION AGENT
    # =====================================================

    try:
        decision = _get_decision_result(
            claim,
            order_id,
        )

    except Exception as exc:
        st.error(
            "The decision pipeline could not complete. "
            "No automatic approval has been issued."
        )

        with st.expander("Technical details"):
            st.exception(exc)

        st.info(
            "Check the policy documents, rebuild the Hybrid RAG "
            "index if needed, verify the Gemini API key and "
            "confirm that the Vision Agent result is available."
        )
        return

    # =====================================================
    # NORMALIZE RESULTS
    # =====================================================

    status = decision.get(
        "status",
        "HUMAN_REVIEW",
    )

    status_labels = {
        "POLICY_SUPPORTS_RETURN": "RETURN SUPPORTED BY POLICY",
        "POLICY_DOES_NOT_SUPPORT_RETURN": (
            "RETURN NOT SUPPORTED BY RETRIEVED POLICY"
        ),
        "HUMAN_REVIEW": "HUMAN REVIEW REQUIRED",
    }

    status_label = status_labels.get(
        status,
        "HUMAN REVIEW REQUIRED",
    )

    sources = decision.get("sources", [])
    citations = decision.get("citations", [])
    findings = decision.get("policy_findings", [])
    missing_information = decision.get(
        "missing_information",
        [],
    )

    if not isinstance(sources, list):
        sources = []

    if not isinstance(citations, list):
        citations = []

    if not isinstance(findings, list):
        findings = [findings] if findings else []

    if not isinstance(missing_information, list):
        missing_information = (
            [missing_information]
            if missing_information
            else []
        )

    rag_result = decision.get("rag_result", {})

    if not isinstance(rag_result, dict):
        rag_result = {}

    needs_review = decision.get(
        "needs_human_review",
        True,
    )

    # If citations or sources are absent, fail safely.
    if not sources or not citations:
        needs_review = True

    # =====================================================
    # MAIN DECISION
    # =====================================================

    st.caption("POLICY-BASED ASSESSMENT")

    with st.container(border=True):

        st.subheader(status_label)

        st.write(
            decision.get(
                "summary",
                "No decision explanation is available.",
            )
        )

        if status == "POLICY_SUPPORTS_RETURN":
            st.info(
                "The retrieved policy supports a preliminary "
                "return assessment. This is not an automatic "
                "refund authorization."
            )

        elif status == "POLICY_DOES_NOT_SUPPORT_RETURN":
            st.warning(
                "The retrieved policy does not support the "
                "return based on the current assessment. "
                "A reviewer should verify the source and "
                "applicable exceptions before rejecting the claim."
            )

        else:
            st.warning(
                "The available evidence is insufficient for a "
                "reliable automated assessment. Human review is required."
            )

        if needs_review:
            st.warning(
                "This claim requires human verification before "
                "a final decision."
            )

    # =====================================================
    # METRICS
    # =====================================================

    st.divider()
    st.subheader("Assessment overview")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Policy assessment",
            status,
        )

    with col2:
        confidence = _normalize_confidence(
            decision.get("model_confidence")
        )

        if confidence is None:
            confidence = _normalize_confidence(
                rag_result.get("confidence")
            )

        st.metric(
            "Model-reported confidence",
            f"{confidence:.0%}" if confidence is not None else "N/A",
        )

    with col3:
        st.metric(
            "Order value",
            f"${purchase_price:,.2f}",
        )

    st.caption(
        "Model-reported confidence is not a calibrated "
        "probability that the assessment is correct."
    )

    # =====================================================
    # DECISION EXPLANATION
    # =====================================================

    st.divider()
    st.caption("DECISION EXPLANATION")
    st.subheader("Why did the system reach this assessment?")

    _display_list(
        findings,
        "No usable policy findings were returned.",
    )

    # =====================================================
    # VISION EVIDENCE
    # =====================================================

    st.divider()
    st.caption("01 / VISUAL EVIDENCE")
    st.subheader("Vision Agent findings")

    if vision_result:

        visual_fields = [
            ("Product category", "product_category"),
            ("Product type", "product_type"),
            ("Damage type", "damage_type"),
            ("Damage location", "damage_location"),
            ("Damage severity", "damage_severity"),
            ("Visual evidence", "visual_evidence"),
            ("Uncertainty", "uncertainty_reason"),
        ]

        for label, key in visual_fields:
            value = vision_result.get(key)

            if value not in (None, ""):
                st.write(f"**{label}:** {_display_value(value)}")

        vision_confidence = _normalize_confidence(
            vision_result.get("confidence")
        )

        if vision_confidence is not None:
            st.metric(
                "Visual confidence",
                f"{vision_confidence:.0%}",
            )

    else:
        st.warning(
            "No Vision Agent result was found in Streamlit session state. "
            "The assessment may lack visual evidence."
        )

    # =====================================================
    # RETRIEVED POLICY EVIDENCE
    # =====================================================

    st.divider()
    st.caption("02 / POLICY EVIDENCE")
    st.subheader("Retrieved policy passages")

    if sources:

        for index, source in enumerate(sources):

            if not isinstance(source, dict):
                continue

            source_id = source.get("id", f"S{index + 1}")
            source_name = source.get(
                "source",
                "Unknown source",
            )
            page = source.get("page", 0)

            title = f"Source {source_id} — {source_name}"

            if page:
                title += f" — page {page}"

            with st.expander(title):

                st.markdown("**Retrieved passage**")

                passage = source.get("text", "")

                if passage:
                    st.write(passage)
                else:
                    st.warning("The source contains no passage text.")

                st.caption(
                    f"Source document: {source_name}"
                )

                if page:
                    st.caption(f"Page: {page}")

                semantic_score = source.get("semantic_score")
                bm25_score = source.get("bm25_score")

                score_col1, score_col2 = st.columns(2)

                with score_col1:
                    if isinstance(semantic_score, (int, float)):
                        st.metric(
                            "Semantic score",
                            f"{semantic_score:.3f}",
                        )

                with score_col2:
                    if isinstance(bm25_score, (int, float)):
                        st.metric(
                            "BM25 score",
                            f"{bm25_score:.3f}",
                        )

    else:
        st.warning(
            "No policy passages were returned. "
            "The system must not rely on unsupported policy claims."
        )

    st.write("")

    if citations:
        st.markdown("**Cited source IDs**")
        st.write(", ".join(str(item) for item in citations))
    else:
        st.warning(
            "No source citations were returned. "
            "Human review is required."
        )

    # =====================================================
    # MISSING INFORMATION
    # =====================================================

    st.divider()
    st.caption("03 / MISSING INFORMATION")
    st.subheader("Information requiring verification")

    if missing_information:
        _display_list(
            missing_information,
            "No missing information was reported.",
        )
    else:
        st.info(
            "The agents did not report missing information. "
            "This does not guarantee that all required facts "
            "have been verified."
        )

    # =====================================================
    # SAFETY GUARDRAILS
    # =====================================================

    st.divider()
    st.caption("04 / SAFETY GUARDRAILS")
    st.subheader("Verification status")

    checks = [
        (
            "Policy passages retrieved",
            bool(sources),
        ),
        (
            "Source citations available",
            bool(citations),
        ),
        (
            "Vision result available",
            bool(vision_result),
        ),
        (
            "Human review not required",
            not needs_review,
        ),
    ]

    for label, passed in checks:
        if passed:
            st.success(f"✓ {label}")
        else:
            st.warning(f"⚠ {label}")

    if needs_review:
        st.warning("Human review is required.")
    else:
        st.info(
            "The agents did not flag this claim for human review. "
            "Final refund authorization remains a separate process."
        )

    # =====================================================
    # TRACEABILITY
    # =====================================================

    st.divider()
    st.caption("DECISION TRACEABILITY")
    st.subheader("Evidence chain")

    col1, col2, col3 = st.columns(3, gap="large")

    with col1:
        with st.container(border=True):
            st.markdown("### Vision Agent")

            st.write(
                vision_result.get(
                    "damage_type",
                    "Damage type not specified",
                )
                if vision_result
                else "Visual result unavailable"
            )

            st.caption(
                "Findings are based on visible image evidence."
            )

    with col2:
        with st.container(border=True):
            st.markdown("### Hybrid RAG")

            st.metric(
                "Retrieved passages",
                len(sources),
            )

            st.caption(
                f"Model: {rag_result.get('model', 'N/A')}"
            )

            st.caption(
                f"Prompt: {rag_result.get('prompt_version', 'N/A')}"
            )

    with col3:
        with st.container(border=True):
            st.markdown("### Decision Agent")

            st.write(status_label)

            st.write(
                "Human review required"
                if needs_review
                else "No review flag returned"
            )

    # =====================================================
    # ORDER SUMMARY
    # =====================================================

    st.divider()
    st.caption("CLAIM SUMMARY")
    st.subheader("Return request details")

    with st.container(border=True):

        col1, col2, col3 = st.columns(3)

        with col1:
            st.caption("ORDER ID")
            st.markdown(f"### {order_id}")

        with col2:
            st.caption("PRODUCT")
            st.markdown(f"### {product_name}")

        with col3:
            st.caption("ORDER VALUE")
            st.markdown(f"### ${purchase_price:,.2f}")

        if description:
            st.markdown("**Customer description**")
            st.write(description)

        delivery_date = claim.get("delivery_date")

        if delivery_date:
            st.markdown("**Delivery date**")
            st.write(str(delivery_date))

    # =====================================================
    # FINAL ACTION
    # =====================================================

    st.divider()

    with st.container(border=True):

        st.caption("NEXT STEP")
        st.subheader("Human verification")

        st.write(
            "This is a preliminary policy assessment. "
            "A human reviewer should verify the applicable policy, "
            "evidence and exceptions before authorizing a refund."
        )

        if st.button(
            "Send to human review",
            use_container_width=True,
            key="send_human_review",
        ):
            st.session_state["page"] = "Human Review"

            st.session_state["claim_for_review"] = {
                "claim": claim,
                "decision": decision,
            }

            st.rerun()
