import streamlit as st

from components.styles import apply_styles
from components.navbar import (
    render_navbar,
    render_navigation
)


def show_return_request():

    apply_styles()

    render_navbar()
    render_navigation()

    st.write("")

    # =========================================================
    # PAGE HEADER
    # =========================================================

    st.caption(
        "RETURN REQUEST  /  STEP 01"
    )

    st.markdown(
        "# Submit your return claim."
    )

    st.write(
        "Provide the order information and visual evidence "
        "needed by our AI verification system."
    )

    st.write("")

    # =========================================================
    # PROGRESS
    # =========================================================

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.success("● 01  Request")

    with col2:
        st.caption("○ 02  AI Analysis")

    with col3:
        st.caption("○ 03  Decision")

    with col4:
        st.caption("○ 04  Review")

    st.write("")

    # =========================================================
    # MAIN LAYOUT
    # =========================================================

    left, right = st.columns(
        [1.15, 0.85],
        gap="large"
    )

    # =========================================================
    # LEFT — CLAIM INFORMATION
    # =========================================================

    with left:

        with st.container(border=True):

            st.caption(
                "01  /  ORDER INFORMATION"
            )

            st.markdown(
                "### 📦 Tell us about your order"
            )

            st.write(
                "Enter the basic information associated "
                "with the product you want to return."
            )

            st.write("")

            col1, col2 = st.columns(2)

            with col1:

                order_id = st.text_input(
                    "Order ID",
                    placeholder="e.g. 45872"
                )

            with col2:

                product_name = st.text_input(
                    "Product",
                    placeholder="e.g. Nike Pegasus 41"
                )

            col1, col2 = st.columns(2)

            with col1:

                product_category = st.selectbox(
                    "Category",
                    [
                        "Footwear",
                        "Clothing",
                        "Electronics",
                        "Home & Kitchen",
                        "Beauty",
                        "Accessories",
                        "Other"
                    ]
                )

            with col2:

                purchase_price = st.number_input(
                    "Purchase price",
                    min_value=0.0,
                    value=120.0,
                    step=1.0
                )

            st.write("")

            st.caption(
                "DELIVERY STATUS"
            )

            delivery_status = st.selectbox(
                "Order status",
                [
                    "Delivered",
                    "In transit",
                    "Pending"
                ]
            )

    # =========================================================
    # RIGHT — IMAGE
    # =========================================================

    with right:

        with st.container(border=True):

            st.caption(
                "02  /  VISUAL EVIDENCE"
            )

            st.markdown(
                "### 📸 Upload product evidence"
            )

            st.write(
                "A clear image helps the Vision Agent "
                "identify visible damage."
            )

            st.write("")

            uploaded_image = st.file_uploader(
                "Upload product image",
                type=[
                    "png",
                    "jpg",
                    "jpeg",
                    "webp"
                ],
                label_visibility="collapsed"
            )

            if uploaded_image:

                st.image(
                    uploaded_image,
                    caption="Uploaded evidence",
                    use_container_width=True
                )

                st.success(
                    "✓ Image ready for AI analysis"
                )

            else:

                st.info(
                    "📷 Upload a clear image of the product."
                )

    # =========================================================
    # DESCRIPTION
    # =========================================================

    st.write("")

    with st.container(border=True):

        st.caption(
            "03  /  CUSTOMER DESCRIPTION"
        )

        st.markdown(
            "### ✍️ What happened to the product?"
        )

        description = st.text_area(
            "Describe the problem",
            placeholder=(
                "Example: The shoes arrived with a stain "
                "on the left shoe."
            ),
            height=150,
            label_visibility="collapsed"
        )

        st.caption(
            "Describe what you observed. The AI will compare "
            "your description with the visual evidence."
        )

    # =========================================================
    # CLAIM SUMMARY
    # =========================================================

    st.write("")

    with st.container(border=True):

        st.caption(
            "CLAIM PREVIEW"
        )

        st.markdown(
            "### Review your information"
        )

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                "ORDER",
                order_id if order_id else "—"
            )

        with col2:

            st.metric(
                "PRODUCT",
                product_name if product_name else "—"
            )

        with col3:

            st.metric(
                "VALUE",
                f"${purchase_price:.2f}"
            )

        st.write("")

        col1, col2 = st.columns(2)

        with col1:

            if uploaded_image:

                st.success(
                    "✓ Visual evidence attached"
                )

            else:

                st.warning(
                    "○ Visual evidence missing"
                )

        with col2:

            if description.strip():

                st.success(
                    "✓ Customer description provided"
                )

            else:

                st.warning(
                    "○ Description missing"
                )

    # =========================================================
    # VALIDATION
    # =========================================================

    st.write("")

    required_fields = (
        order_id.strip()
        and product_name.strip()
        and description.strip()
        and uploaded_image is not None
    )

    if not required_fields:

        st.info(
            "💡 Complete the order information, "
            "description and image before starting the analysis."
        )

    # =========================================================
    # ACTION
    # =========================================================

    st.write("")

    col1, col2, col3 = st.columns(
        [1, 1.5, 1]
    )

    with col2:

        if st.button(
            "🔍  Analyze my claim",
            use_container_width=True,
            key="analyze_claim"
        ):

            if not required_fields:

                st.error(
                    "Please complete all required fields."
                )

            else:

                # =================================================
                # SAVE CLAIM INFORMATION
                # =================================================

                st.session_state.order_id = order_id

                st.session_state.product_name = (
                    product_name
                )

                st.session_state.product_category = (
                    product_category
                )

                st.session_state.purchase_price = (
                    purchase_price
                )

                st.session_state.delivery_status = (
                    delivery_status
                )

                st.session_state.description = (
                    description
                )

                # =================================================
                # SAVE IMAGE AS BYTES
                # =================================================

                image_bytes = (
                    uploaded_image.getvalue()
                )

                st.session_state.image_bytes = (
                    image_bytes
                )

                st.session_state.image_mime_type = (
                    uploaded_image.type
                )

                # =================================================
                # RESET PREVIOUS VISION RESULT
                # =================================================

                st.session_state.pop(
                    "vision_result",
                    None
                )

                # =================================================
                # GO TO AI ANALYSIS
                # =================================================

                st.session_state.page = (
                    "AI Analysis"
                )

                st.rerun()

    # =========================================================
    # INFORMATION
    # =========================================================

    st.write("")

    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:

        st.caption(
            "🔐 SECURE"
        )

        st.write(
            "Your claim information is used only "
            "for the verification workflow."
        )

    with col2:

        st.caption(
            "👁️ MULTIMODAL"
        )

        st.write(
            "The Vision Agent analyzes both "
            "your image and description."
        )

    with col3:

        st.caption(
            "🧑‍💼 HUMAN ESCALATION"
        )

        st.write(
            "Uncertain claims can be sent "
            "to a human reviewer."
        )