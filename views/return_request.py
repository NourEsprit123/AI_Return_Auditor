import os
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

import streamlit as st
from io import BytesIO
from PIL import Image

from components.styles import apply_styles
from components.navbar import render_navbar, render_navigation


def show_return_request():

    apply_styles()
    render_navbar()
    render_navigation()

    st.write("")

    st.caption("RETURN REQUEST  /  STEP 01")
    st.markdown("# Submit your return claim.")
    st.write(
        "Provide the order information and visual evidence "
        "needed by our AI verification system."
    )
    st.write("")

    # =========================================================
    # PROGRESS
    # =========================================================

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.success("● 01  Request")
    with col2: st.caption("○ 02  AI Analysis")
    with col3: st.caption("○ 03  Decision")
    with col4: st.caption("○ 04  Review")

    st.write("")

    # =========================================================
    # SECTION 00 — WARRANTY / PURCHASE DOCUMENT (optional)
    # =========================================================

    with st.container(border=True):

        st.caption("00  /  WARRANTY OR PURCHASE DOCUMENT  —  OPTIONAL")

        st.markdown("### 📄 Upload your warranty card or receipt")

        st.write(
            "Upload a photo or scan of your warranty card, purchase receipt, "
            "or invoice. The AI will automatically extract the order information "
            "and pre-fill the form below."
        )

        st.write("")

        doc_file = st.file_uploader(
            "Upload document",
            type=["png", "jpg", "jpeg", "webp", "pdf"],
            key="warranty_doc",
            label_visibility="collapsed",
        )

        # Store extracted values in session state
        if "doc_extracted" not in st.session_state:
            st.session_state.doc_extracted = {}

        if doc_file is not None:

            # Only extract if this is a new file
            if st.session_state.get("doc_file_name") != doc_file.name:

                st.session_state.doc_file_name = doc_file.name

                col1, col2 = st.columns([1, 2])

                with col1:
                    try:
                        if doc_file.type == "application/pdf":
                            st.info("📄 PDF document uploaded")
                        else:
                            doc_image = Image.open(BytesIO(doc_file.getvalue())).convert("RGB")
                            st.image(doc_image, caption="Uploaded document", use_container_width=True)
                    except Exception:
                        st.info("📄 Document uploaded")

                with col2:
                    with st.spinner("🤖 Extracting information from document..."):
                        try:
                            from agents.document_agent import DocumentAgent
                            agent = DocumentAgent()
                            is_pdf = doc_file.type == "application/pdf"
                            if is_pdf:
                                extraction = agent.extract(doc_file.getvalue(), is_pdf=True)
                            else:
                                doc_image_pil = Image.open(BytesIO(doc_file.getvalue())).convert("RGB")
                                extraction = agent.extract(doc_image_pil, is_pdf=False)
                            st.session_state.doc_extracted = extraction.model_dump()
                        except Exception as exc:
                            st.session_state.doc_extracted = {
                                "extraction_successful": False,
                                "extraction_notes": str(exc),
                            }

                extraction = st.session_state.doc_extracted

                if extraction.get("extraction_successful"):
                    st.success("✓ Information extracted successfully. Fields have been pre-filled below.")
                    # Show what was found
                    found = []
                    if extraction.get("product_name"):   found.append(f"Product: **{extraction['product_name']}**")
                    if extraction.get("order_id"):        found.append(f"Order ID: **{extraction['order_id']}**")
                    if extraction.get("purchase_date"):   found.append(f"Date: **{extraction['purchase_date']}**")
                    if extraction.get("purchase_price"):  found.append(f"Price: **{extraction['purchase_price']}**")
                    if extraction.get("store_name"):      found.append(f"Store: **{extraction['store_name']}**")
                    for item in found:
                        st.write(f"  • {item}")
                else:
                    st.warning(
                        "⚠️ Could not extract information from this document. "
                        f"{extraction.get('extraction_notes', '')} "
                        "Please fill the form below manually."
                    )

            else:
                # File already processed — show status
                extraction = st.session_state.doc_extracted
                col1, col2 = st.columns([1, 2])
                with col1:
                    try:
                        if doc_file.type == "application/pdf":
                            st.info("📄 PDF document uploaded")
                        else:
                            doc_image = Image.open(BytesIO(doc_file.getvalue())).convert("RGB")
                            st.image(doc_image, use_container_width=True)
                    except Exception:
                        st.info("📄 Document uploaded")
                with col2:
                    if extraction.get("extraction_successful"):
                        st.success("✓ Document already processed.")
                    else:
                        st.warning("⚠️ Could not extract from document. Fill form manually.")

    st.write("")

    # =========================================================
    # Get pre-filled values from extraction (if available)
    # =========================================================

    ext = st.session_state.get("doc_extracted", {})

    prefill_order_id    = ext.get("order_id", "")
    prefill_product     = ext.get("product_name", "")
    prefill_category    = ext.get("product_category", "")
    prefill_price       = ext.get("purchase_price", "")

    # Convert price string to float safely
    try:
        prefill_price_float = float(prefill_price) if prefill_price else 120.0
    except ValueError:
        prefill_price_float = 120.0

    # Map category to selectbox index
    categories = ["Footwear", "Clothing", "Electronics", "Home & Kitchen", "Beauty", "Accessories", "Other"]
    if prefill_category in categories:
        cat_index = categories.index(prefill_category)
    else:
        cat_index = 0

    # =========================================================
    # MAIN LAYOUT
    # =========================================================

    left, right = st.columns([1.15, 0.85], gap="large")

    # =========================================================
    # LEFT — ORDER INFORMATION
    # =========================================================

    with left:

        with st.container(border=True):

            st.caption("01  /  ORDER INFORMATION")
            st.markdown("### 📦 Tell us about your order")
            st.write(
                "Enter or verify the order information. "
                "Fields pre-filled from your document can be edited."
            )
            st.write("")

            col1, col2 = st.columns(2)

            with col1:
                order_id = st.text_input(
                    "Order ID",
                    value=prefill_order_id,
                    placeholder="e.g. 45872",
                )

            with col2:
                product_name = st.text_input(
                    "Product",
                    value=prefill_product,
                    placeholder="e.g. Nike Pegasus 41",
                )

            col1, col2 = st.columns(2)

            with col1:
                product_category = st.selectbox(
                    "Category",
                    categories,
                    index=cat_index,
                )

            with col2:
                purchase_price = st.number_input(
                    "Purchase price",
                    min_value=0.0,
                    value=prefill_price_float,
                    step=1.0,
                )

            st.write("")
            st.caption("DELIVERY STATUS")

            delivery_status = st.selectbox(
                "Order status",
                ["Delivered", "In transit", "Pending"],
            )

            # Show purchase date if extracted
            if ext.get("purchase_date"):
                st.write("")
                st.caption("PURCHASE DATE  (from document)")
                st.info(f"📅 {ext['purchase_date']}")

            if ext.get("store_name"):
                st.caption("STORE  (from document)")
                st.info(f"🏪 {ext['store_name']}")

    # =========================================================
    # RIGHT — PRODUCT IMAGE
    # =========================================================

    with right:

        with st.container(border=True):

            st.caption("02  /  VISUAL EVIDENCE")
            st.markdown("### 📸 Upload product evidence")
            st.write("A clear image helps the Vision Agent identify visible damage.")
            st.write("")

            uploaded_image = st.file_uploader(
                "Upload product image",
                type=["png", "jpg", "jpeg", "webp"],
                label_visibility="collapsed",
                key="product_image",
            )

            if uploaded_image:
                st.image(
                    uploaded_image,
                    caption="Uploaded evidence",
                    use_container_width=True,
                )
                st.success("✓ Image ready for AI analysis")
            else:
                st.info("📷 Upload a clear image of the product.")

    # =========================================================
    # DESCRIPTION
    # =========================================================

    st.write("")

    with st.container(border=True):

        st.caption("03  /  CUSTOMER DESCRIPTION")
        st.markdown("### ✍️ What happened to the product?")

        description = st.text_area(
            "Describe the problem",
            placeholder="Example: The shoes arrived with a stain on the left shoe.",
            height=150,
            label_visibility="collapsed",
        )

        st.caption(
            "Describe what you observed. The AI will compare "
            "your description with the visual evidence."
        )

    # =========================================================
    # CLAIM PREVIEW
    # =========================================================

    st.write("")

    with st.container(border=True):

        st.caption("CLAIM PREVIEW")
        st.markdown("### Review your information")

        col1, col2, col3 = st.columns(3)
        with col1: st.metric("ORDER", order_id if order_id else "—")
        with col2: st.metric("PRODUCT", product_name if product_name else "—")
        with col3: st.metric("VALUE", f"${purchase_price:.2f}")

        st.write("")

        col1, col2 = st.columns(2)
        with col1:
            if uploaded_image:
                st.success("✓ Visual evidence attached")
            else:
                st.warning("○ Visual evidence missing")
        with col2:
            if description.strip():
                st.success("✓ Customer description provided")
            else:
                st.warning("○ Description missing")

    # =========================================================
    # VALIDATION & ACTION
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
            "💡 Complete the order information, description and image before starting the analysis."
        )

    st.write("")

    col1, col2, col3 = st.columns([1, 1.5, 1])

    with col2:

        if st.button("🔍  Analyze my claim", use_container_width=True, key="analyze_claim"):

            if not required_fields:
                st.error("Please complete all required fields.")

            else:

                # Save to session state
                st.session_state.order_id         = order_id
                st.session_state.product_name     = product_name
                st.session_state.product_category = product_category
                st.session_state.purchase_price   = purchase_price
                st.session_state.delivery_status  = delivery_status
                st.session_state.description      = description

                # Save purchase date from document if available
                if ext.get("purchase_date"):
                    st.session_state.purchase_date = ext["purchase_date"]

                # Save image bytes
                st.session_state.image_bytes     = uploaded_image.getvalue()
                st.session_state.image_mime_type = uploaded_image.type

                # Reset previous analysis
                for key in ["vision_result", "vision_agent_state", "rag_result", "decision_result", "order_info"]:
                    st.session_state.pop(key, None)

                st.session_state.page = "AI Analysis"
                st.rerun()

    # =========================================================
    # INFO FOOTER
    # =========================================================

    st.write("")
    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.caption("📄 DOCUMENT SCAN")
        st.write("Upload your warranty or receipt to auto-fill the order form.")

    with col2:
        st.caption("👁️ MULTIMODAL")
        st.write("The Vision Agent analyzes both your image and description.")

    with col3:
        st.caption("🧑‍💼 HUMAN ESCALATION")
        st.write("Uncertain claims can be sent to a human reviewer.")
