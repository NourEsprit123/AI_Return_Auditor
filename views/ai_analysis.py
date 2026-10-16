

import streamlit as st

import base64

import requests

from io import BytesIO

from PIL import Image

from components.styles import apply_styles

from components.navbar import render_navbar, render_navigation


N8N_WEBHOOK_URL = "http://localhost:5678/webhook/vision-analysis"


def show_ai_analysis():

    apply_styles()

    render_navbar()

    render_navigation()

    st.write("")

    st.caption("AI ANALYSIS  /  STEP 02")

    st.markdown("# Intelligence is analyzing your claim.")

    st.write(

        "The Vision Agent analyzes the product image "

        "and compares it with the customer's description."

    )

    st.write("")

    # ==========================================================

    # CLAIM INFORMATION

    # ==========================================================

    order_id = st.session_state.get("order_id", "—")

    product_name = st.session_state.get("product_name", "Unknown product")

    category = st.session_state.get("product_category", "Unknown")

    description = st.session_state.get("description", "")

    image_bytes = st.session_state.get("image_bytes")

    # ==========================================================

    # CLAIM SUMMARY

    # ==========================================================

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

            st.caption("AGENT")

            st.info("VISION AI")

    st.write("")

    # ==========================================================

    # VALIDATION

    # ==========================================================

    if image_bytes is None:

        st.error(

            "No image was provided. "

            "Please return to the Return Request page."

        )

        if st.button(

            "← Back to return request",

            key="back_to_request",

        ):

            st.session_state.page = "Return Request"

            st.rerun()

        return

    if not description.strip():

        st.error("No customer description was provided.")

        if st.button(

            "← Back to return request",

            key="back_to_request_description",

        ):

            st.session_state.page = "Return Request"

            st.rerun()

        return

    # ==========================================================

    # LOAD IMAGE FROM SESSION STATE

    # ==========================================================

    try:

        image = Image.open(BytesIO(image_bytes))

        image.load()

        image = image.convert("RGB")

    except Exception as exc:

        st.error(f"Unable to read the uploaded image: {exc}")

        return

    # ==========================================================

    # RUN VISION AGENT

    # ==========================================================

    if "vision_result" not in st.session_state:

        st.caption("AI VERIFICATION PIPELINE")

        st.markdown("## Multimodal Vision Analysis")

        st.write(

            "Gemini will inspect the visual evidence "

            "and compare it with the customer's description."

        )

        st.write("")

        left, right = st.columns([0.9, 1.1], gap="large")

        # ------------------------------------------------------

        # IMAGE

        # ------------------------------------------------------

        with left:

            with st.container(border=True):

                st.caption("VISUAL EVIDENCE")

                st.image(

                    image,

                    caption="Customer-provided image",

                    use_container_width=True,

                )

        # ------------------------------------------------------

        # DESCRIPTION

        # ------------------------------------------------------

        with right:

            with st.container(border=True):

                st.caption("CUSTOMER DESCRIPTION")

                st.markdown("### 💬 What the customer reported")

                st.info(description)

                st.write("")

                st.caption("VISION AGENT")

                st.write(

                    "The agent will analyze the image "

                    "and produce structured evidence."

                )

        st.write("")

        col1, col2, col3 = st.columns([1, 1.5, 1])

        with col2:

            if st.button(

                "🔍  Run Vision Agent",

                use_container_width=True,

                key="run_vision_agent",

            ):

                try:
                    with st.status(
                        "Running Vision Agent through n8n...",
                        expanded=True,
                    ) as status:
                        st.write("Preparing image for n8n...")

                        image_base64 = base64.b64encode(
                            image_bytes
                        ).decode("utf-8")

                        payload = {
                            "image_base64": image_base64,
                            "customer_description": description,
                        }

                        st.write("Sending request to n8n...")
                        response = requests.post(
                            N8N_WEBHOOK_URL,
                            json=payload,
                            timeout=360,
                        )
                        response.raise_for_status()
                        data = response.json()

                        result = data.get("result")
                        agent_state = data.get("state", {})

                        if not isinstance(result, dict):
                            raise ValueError(
                                "n8n did not return a valid result object."
                            )

                        st.session_state.vision_result = result
                        st.session_state.vision_agent_state = agent_state

                        status.update(
                            label="Vision analysis completed!",
                            state="complete",
                        )

                    st.success(
                        "✓ Vision analysis completed successfully."
                    )
                    st.rerun()

                except requests.RequestException as exc:
                    st.error("Unable to communicate with n8n.")
                    st.exception(exc)

                except (ValueError, TypeError) as exc:
                    st.error("The response returned by n8n is invalid.")
                    st.exception(exc)

                except Exception as exc:
                    st.error("Vision analysis failed.")
                    st.exception(exc)

        return

    # ==========================================================

    # DISPLAY VISION RESULT

    # ==========================================================

    result = st.session_state.get("vision_result")

    if not result:

        st.warning("No Vision Agent result available.")

        return

    confidence = float(result.get("confidence", 0))

    confidence_percent = confidence * 100

    severity = result.get("severity", "Unknown")

    consistency = result.get("description_consistency", "Unknown")

    # ==========================================================

    # RESULT HEADER

    # ==========================================================

    st.caption("VISION AGENT  /  COMPLETED")

    st.markdown("## What the AI found")

    st.write(

        "The following results were generated directly "

        "from the multimodal Vision Agent."

    )

    st.write("")

    # ==========================================================

    # MAIN METRICS

    # ==========================================================

    with st.container(border=True):

        col1, col2, col3 = st.columns([1.2, 0.8, 1.2])

        with col1:

            st.caption("VISION CONFIDENCE")

            st.markdown(f"# {confidence_percent:.0f}%")

            st.progress(max(0.0, min(confidence, 1.0)))

        with col2:

            st.caption("SEVERITY")

            if severity.lower() == "high":

                st.error(f"⚠ {severity}")

            elif severity.lower() == "medium":

                st.warning(f"⚠ {severity}")

            elif severity.lower() == "low":

                st.info(f"● {severity}")

            else:

                st.info(f"● {severity}")

        with col3:

            st.caption("DESCRIPTION CONSISTENCY")

            if (

                "consistent" in consistency.lower()

                and "inconsistent" not in consistency.lower()

            ):

                st.success("✓ CONSISTENT")

            else:

                st.warning("⚠ INCONSISTENT")

    st.write("")

    # ==========================================================

    # IMAGE + DETECTED ATTRIBUTES

    # ==========================================================

    left, right = st.columns([0.9, 1.1], gap="large")

    # ----------------------------------------------------------

    # IMAGE

    # ----------------------------------------------------------

    with left:

        with st.container(border=True):

            st.caption("VISUAL EVIDENCE")

            st.image(

                image,

                caption="Analyzed product",

                use_container_width=True,

            )

    # ----------------------------------------------------------

    # ATTRIBUTES

    # ----------------------------------------------------------

    with right:

        with st.container(border=True):

            st.caption("DETECTED ATTRIBUTES")

            st.markdown("### AI observations")

            col1, col2 = st.columns(2)

            with col1:

                st.caption("PRODUCT TYPE")

                st.write(

                    result.get("product_type", "Unknown")

                )

            with col2:

                st.caption("CATEGORY")

                st.write(

                    result.get("product_category", "Unknown")

                )

            st.divider()

            # Full-width display for long damage descriptions.

            # st.write() wraps text instead of constraining it

            # inside a small metric component.

            st.markdown("**DAMAGE TYPE**")

            st.write(

                result.get("damage_type", "Unknown")

            )

            st.write("")

            st.markdown("**DAMAGE LOCATION**")

            st.write(

                result.get("damage_location", "Unknown")

            )

            st.write("")

            st.caption("SEVERITY")

            if severity.lower() == "high":

                st.error(f"⚠ {severity}")

            elif severity.lower() == "medium":

                st.warning(f"⚠ {severity}")

            elif severity.lower() == "low":

                st.info(f"● {severity}")

            elif severity.lower() == "none":

                st.success("✓ No visible damage")

            else:

                st.info(f"● {severity}")

    st.write("")

    # ==========================================================

    # VISUAL EVIDENCE

    # ==========================================================

    with st.container(border=True):

        st.caption("VISUAL EVIDENCE")

        st.markdown("### 🔎 What the model observed")

        st.write(

            result.get(

                "visual_evidence",

                "No visual evidence description.",

            )

        )

    st.write("")

    # ==========================================================

    # DESCRIPTION CONSISTENCY

    # ==========================================================

    with st.container(border=True):

        st.caption("CUSTOMER / IMAGE CONSISTENCY")

        st.markdown("### 💬 Comparison with customer description")

        if (

            "consistent" in consistency.lower()

            and "inconsistent" not in consistency.lower()

        ):

            st.success(consistency)

        else:

            st.warning(consistency)

    st.write("")

    # ==========================================================

    # UNCERTAINTY

    # ==========================================================

    with st.container(border=True):

        st.caption("MODEL UNCERTAINTY")

        st.markdown("### ⚠️ What remains uncertain?")

        uncertainty = result.get(

            "uncertainty",

            "No important uncertainty detected.",

        )

        st.write(uncertainty)

    st.write("")

    # ==========================================================

    # IMPORTANT GUARDRAIL

    # ==========================================================

    if (

        "inconsistent" in consistency.lower()

        or "contradict" in consistency.lower()

        or "does not match" in consistency.lower()

    ):

        st.warning(

            "⚠️ The visual evidence does not match the "

            "customer description. This claim should not "

            "be automatically approved."

        )

    else:

        st.success(

            "✓ The visual evidence is consistent with "

            "the customer description."

        )

    st.write("")

    # ==========================================================

    # STRUCTURED OUTPUT

    # ==========================================================

    st.divider()

    st.caption("STRUCTURED AI OUTPUT")

    st.markdown("## VisionAnalysis")

    with st.expander("View structured result"):

        st.json(result)

        agent_state = st.session_state.get("vision_agent_state")

        if agent_state:

            st.divider()

            st.markdown("### Agent execution state")

            st.json(agent_state)

    st.write("")

    # ==========================================================

    # NAVIGATION

    # ==========================================================

    col1, col2, col3 = st.columns([1, 1.5, 1])

    with col2:

        if st.button(

            "✓  Continue to decision",

            use_container_width=True,

            key="continue_decision_real",

        ):

            st.session_state.page = "Decision"

            st.rerun()

    st.write("")

    if st.button(

        "↻  Run Vision Agent again",

        key="rerun_vision_agent",

    ):

        st.session_state.pop("vision_result", None)

        st.session_state.pop("vision_agent_state", None)

        st.rerun()
