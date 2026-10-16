
import base64
import hashlib
from datetime import datetime

import requests
import streamlit as st

from components.styles import apply_styles
from components.navbar import (
    render_navbar,
    render_navigation,
)


# =========================================================
# CONFIGURATION
# =========================================================

ORDER_EXTRACTION_API_URL = (
    "http://127.0.0.1:8000/extract-order"
)

DOCUMENT_WIDGET_KEY = "order_document"

VERIFIED_FIELD_KEYS = [
    "verified_order_id",
    "verified_order_date",
    "verified_product_name",
    "verified_product_category",
    "verified_customer_name",
    "verified_company_name",
    "verified_delivery_date",
    "verified_purchase_price",
    "verified_quantity",
    "verified_currency",
    "verified_delivery_status",
]


def clear_order_extraction():
    """Clear extracted data and its editable form fields."""

    st.session_state.pop("order_extraction", None)
    st.session_state.pop("order_extraction_signature", None)

    for key in VERIFIED_FIELD_KEYS:
        st.session_state.pop(key, None)


def show_return_request():

    apply_styles()
    render_navbar()
    render_navigation()

    st.write("")

    # =========================================================
    # PAGE HEADER
    # =========================================================

    st.caption("RETURN REQUEST / STEP 01")

    st.markdown("# Submit your return claim.")

    st.write(
        "Upload your order document, provide a photo of the "
        "product, and describe the problem."
    )

    st.write("")

    # =========================================================
    # PROGRESS
    # =========================================================

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.success("● 01 Request")

    with col2:
        st.caption("○ 02 AI Analysis")

    with col3:
        st.caption("○ 03 Decision")

    with col4:
        st.caption("○ 04 Review")

    st.write("")

    # =========================================================
    # MAIN LAYOUT
    # =========================================================

    left, right = st.columns(
        [1.15, 0.85],
        gap="large",
    )

    # =========================================================
    # LEFT — ORDER DOCUMENT AND EXTRACTION
    # =========================================================

    with left:

        with st.container(border=True):

            st.caption("01 / ORDER DOCUMENT")

            st.markdown("### Upload your order document")

            st.write(
                "Upload an invoice, order confirmation, or "
                "other order document. Include the company "
                "stamp if it is present."
            )

            uploaded_document = st.file_uploader(
                "Order document",
                type=["png", "jpg", "jpeg", "jfif", "webp"],
                key=DOCUMENT_WIDGET_KEY,
                help=(
                    "This first version accepts images. "
                    "PDF documents are not yet supported."
                ),
            )

            # Detect a changed document and invalidate
            # extraction results from the previous document.
            if uploaded_document is not None:

                document_bytes = uploaded_document.getvalue()

                document_signature = hashlib.sha256(
                    document_bytes
                ).hexdigest()

                previous_signature = (
                    st.session_state.get(
                        "order_extraction_signature"
                    )
                )

                if (
                    previous_signature is not None
                    and previous_signature != document_signature
                ):
                    clear_order_extraction()

                st.session_state.current_document_signature = (
                    document_signature
                )

                st.image(
                    document_bytes,
                    caption="Uploaded order document",
                    use_container_width=True,
                )

            else:

                st.session_state.pop(
                    "current_document_signature",
                    None,
                )

                if st.session_state.get(
                    "order_extraction_signature"
                ) is not None:
                    clear_order_extraction()

                st.info(
                    "Upload a readable image of your order document."
                )

            st.write("")

            # -------------------------------------------------
            # EXTRACT ORDER INFORMATION
            # -------------------------------------------------

            if st.button(
                "Extract order information",
                use_container_width=True,
                key="extract_order_information",
                disabled=uploaded_document is None,
            ):

                try:

                    document_bytes = (
                        uploaded_document.getvalue()
                    )

                    document_signature = hashlib.sha256(
                        document_bytes
                    ).hexdigest()

                    payload = {
                        "document_base64": base64.b64encode(
                            document_bytes
                        ).decode("utf-8"),
                    }

                    with st.spinner(
                        "Gemini is reading your order document..."
                    ):

                        response = requests.post(
                            ORDER_EXTRACTION_API_URL,
                            json=payload,
                            timeout=120,
                        )

                        response.raise_for_status()

                        response_data = response.json()

                        extraction = response_data.get("result")

                        if not isinstance(extraction, dict):
                            raise ValueError(
                                "The API did not return a valid "
                                "extraction result."
                            )

                        required_result_fields = [
                            "order_number",
                            "product_name",
                            "product_category",
                            "delivery_date",
                            "total_amount",
                            "stamp_detected",
                        ]

                        missing_fields = [
                            field
                            for field in required_result_fields
                            if field not in extraction
                        ]

                        if missing_fields:
                            raise ValueError(
                                "The extraction response is missing "
                                "fields: "
                                + ", ".join(missing_fields)
                            )

                        # Save extraction and associate it with
                        # the exact uploaded document.
                        st.session_state.order_extraction = (
                            extraction
                        )

                        st.session_state.order_extraction_signature = (
                            document_signature
                        )

                        # Reset old editable values so the new
                        # extraction can populate the form.
                        for key in VERIFIED_FIELD_KEYS:
                            st.session_state.pop(key, None)

                        st.session_state.pop(
                            "vision_result",
                            None,
                        )

                        st.session_state.pop(
                            "vision_agent_state",
                            None,
                        )

                    st.success(
                        "Order information extracted successfully."
                    )

                    st.rerun()

                except requests.RequestException as exc:

                    st.error(
                        "Unable to communicate with the extraction API."
                    )

                    st.caption(str(exc))

                    if (
                        getattr(exc, "response", None)
                        is not None
                    ):
                        st.code(
                            exc.response.text[:2000]
                        )

                except (ValueError, TypeError, KeyError) as exc:

                    st.error(
                        "The extraction result is invalid."
                    )

                    st.caption(str(exc))

                except Exception as exc:

                    st.error("Order extraction failed.")

                    st.caption(str(exc))

            # -------------------------------------------------
            # DISPLAY EXTRACTED DATA FOR REVIEW
            # -------------------------------------------------

            extraction = st.session_state.get(
                "order_extraction"
            )

            if extraction:

                st.divider()

                st.markdown("### Review order information")

                st.write(
                    "Verify the extracted values. You can correct "
                    "them before submitting your return claim."
                )

                uncertain_fields = extraction.get(
                    "uncertain_fields",
                    [],
                )

                if uncertain_fields:

                    st.warning(
                        "Some fields require manual verification: "
                        + ", ".join(uncertain_fields)
                    )

                # Order number
                order_id = st.text_input(
                    "Order ID",
                    value=(
                        extraction.get("order_number") or ""
                    ),
                    key="verified_order_id",
                )

                # Order date
                order_date = st.text_input(
                    "Order date (YYYY-MM-DD)",
                    value=(
                        extraction.get("order_date") or ""
                    ),
                    key="verified_order_date",
                )

                # Product name
                product_name = st.text_input(
                    "Product name",
                    value=(
                        extraction.get("product_name") or ""
                    ),
                    key="verified_product_name",
                )

                # Product category
                product_category = st.text_input(
                    "Product category",
                    value=(
                        extraction.get("product_category") or ""
                    ),
                    key="verified_product_category",
                )

                # Customer
                customer_name = st.text_input(
                    "Customer name",
                    value=(
                        extraction.get("customer_name") or ""
                    ),
                    key="verified_customer_name",
                )

                # Company
                company_name = st.text_input(
                    "Company name",
                    value=(
                        extraction.get("company_name") or ""
                    ),
                    key="verified_company_name",
                )

                # Delivery date
                delivery_date = st.text_input(
                    "Delivery date (YYYY-MM-DD)",
                    value=(
                        extraction.get("delivery_date") or ""
                    ),
                    key="verified_delivery_date",
                    help=(
                        "Correct the date if necessary. "
                        "Leave blank if it is unavailable."
                    ),
                )

                # Amount
                extracted_amount = extraction.get(
                    "total_amount"
                )

                try:
                    default_amount = (
                        float(extracted_amount)
                        if extracted_amount is not None
                        else 0.0
                    )

                    if default_amount < 0:
                        default_amount = 0.0

                except (ValueError, TypeError):
                    default_amount = 0.0

                purchase_price = st.number_input(
                    "Order amount",
                    min_value=0.0,
                    value=default_amount,
                    step=1.0,
                    key="verified_purchase_price",
                )

                # Quantity
                extracted_quantity = extraction.get("quantity")

                try:
                    default_quantity = max(
                        1,
                        int(extracted_quantity or 1),
                    )
                except (ValueError, TypeError):
                    default_quantity = 1

                quantity = st.number_input(
                    "Quantity",
                    min_value=1,
                    value=default_quantity,
                    step=1,
                    key="verified_quantity",
                )

                # Currency
                currency = st.text_input(
                    "Currency",
                    value=extraction.get("currency") or "",
                    key="verified_currency",
                )

                # Delivery status is not inferred from the invoice.
                delivery_status = st.selectbox(
                    "Delivery status",
                    ["Unknown", "Delivered"],
                    key="verified_delivery_status",
                    help=(
                        "The presence of an invoice alone does "
                        "not confirm delivery."
                    ),
                )

                # Stamp observation
                stamp_detected = extraction.get(
                    "stamp_detected",
                    False,
                )

                if stamp_detected:
                    st.success(
                        "A visible company stamp or seal was detected."
                    )
                else:
                    st.info(
                        "No company stamp was identified, or its "
                        "presence could not be determined."
                    )

                stamp_description = extraction.get(
                    "stamp_description",
                    "",
                )

                if stamp_description:
                    st.caption(stamp_description)

                document_notes = extraction.get(
                    "document_notes",
                    "",
                )

                if document_notes:
                    st.caption(
                        f"Document notes: {document_notes}"
                    )

                st.warning(
                    "The extracted values have not been verified "
                    "against an authoritative order database. "
                    "A detected stamp does not prove authenticity."
                )

            else:

                order_id = ""
                order_date = ""
                product_name = ""
                product_category = ""
                customer_name = ""
                company_name = ""
                delivery_date = ""
                purchase_price = 0.0
                quantity = 1
                currency = ""
                delivery_status = "Unknown"
                stamp_detected = False

    # =========================================================
    # RIGHT — PRODUCT IMAGE
    # =========================================================

    with right:

        with st.container(border=True):

            st.caption("02 / VISUAL EVIDENCE")

            st.markdown("### Upload product evidence")

            st.write(
                "Upload a clear photo of the product so the "
                "Vision Agent can inspect visible damage."
            )

            uploaded_image = st.file_uploader(
                "Upload product image",
                type=["png", "jpg", "jpeg", "webp"],
                key="product_evidence_image",
                label_visibility="collapsed",
            )

            if uploaded_image:

                st.image(
                    uploaded_image,
                    caption="Uploaded product evidence",
                    use_container_width=True,
                )

                st.success("Product image attached.")

            else:

                st.info(
                    "Upload a clear photo of the damaged product."
                )

    # =========================================================
    # CUSTOMER DESCRIPTION
    # =========================================================

    st.write("")

    with st.container(border=True):

        st.caption("03 / CUSTOMER DESCRIPTION")

        st.markdown("### What happened to the product?")

        description = st.text_area(
            "Describe the problem",
            placeholder=(
                "Example: The shoes arrived with a stain "
                "on the left shoe."
            ),
            height=150,
            key="customer_problem_description",
            label_visibility="collapsed",
        )

        st.caption(
            "Describe what you observed. The Vision Agent will "
            "compare your description with the product photo."
        )

    # =========================================================
    # CLAIM PREVIEW
    # =========================================================

    st.write("")

    with st.container(border=True):

        st.caption("CLAIM PREVIEW")

        st.markdown("### Review your information")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "ORDER",
                order_id or "—",
            )

        with col2:
            st.metric(
                "PRODUCT",
                product_name or "—",
            )

        with col3:
            amount_label = (
                f"{purchase_price:.2f} {currency}".strip()
                if st.session_state.get("order_extraction")
                else "—"
            )

            st.metric(
                "VALUE",
                amount_label,
            )

        with col4:

            formatted_delivery_date = "—"

            if delivery_date:

                try:
                    parsed_date = datetime.strptime(
                        delivery_date.strip(),
                        "%Y-%m-%d",
                    )

                    formatted_delivery_date = (
                        parsed_date.strftime("%d/%m/%Y")
                    )

                except ValueError:
                    formatted_delivery_date = delivery_date

            st.metric(
                "DELIVERY DATE",
                formatted_delivery_date,
            )

        st.write("")

        col1, col2 = st.columns(2)

        with col1:

            if uploaded_image:
                st.success("Product photo attached.")
            else:
                st.warning("Product photo missing.")

        with col2:

            if description.strip():
                st.success("Customer description provided.")
            else:
                st.warning("Customer description missing.")

        if not st.session_state.get("order_extraction"):
            st.info(
                "Upload your order document and extract its "
                "information before continuing."
            )

    # =========================================================
    # VALIDATION
    # =========================================================

    st.write("")

    extraction = st.session_state.get("order_extraction")

    current_signature = st.session_state.get(
        "current_document_signature"
    )

    extracted_signature = st.session_state.get(
        "order_extraction_signature"
    )

    extraction_matches_document = (
        bool(extraction)
        and bool(current_signature)
        and current_signature == extracted_signature
    )

    valid_delivery_date = True

    if delivery_date.strip():

        try:
            datetime.strptime(
                delivery_date.strip(),
                "%Y-%m-%d",
            )

        except ValueError:
            valid_delivery_date = False

    required_fields = (
        extraction_matches_document
        and bool(order_id.strip())
        and bool(product_name.strip())
        and bool(description.strip())
        and uploaded_image is not None
        and valid_delivery_date
    )

    if not extraction_matches_document:

        st.info(
            "Upload an order document and extract its information "
            "before starting the analysis."
        )

    elif not valid_delivery_date:

        st.warning(
            "The delivery date must use YYYY-MM-DD format, "
            "or be left blank."
        )

    elif not required_fields:

        st.info(
            "Complete the required information, upload the product "
            "photo and describe the problem."
        )

    # =========================================================
    # ACTION — CONTINUE TO AI ANALYSIS
    # =========================================================

    st.write("")

    col1, col2, col3 = st.columns([1, 1.5, 1])

    with col2:

        if st.button(
            "Analyze my claim",
            use_container_width=True,
            key="analyze_claim",
        ):

            if not required_fields:

                st.error(
                    "Please complete the required fields and "
                    "correct any invalid date."
                )

            else:

                # ---------------------------------------------
                # SAVE VERIFIED ORDER INFORMATION
                # ---------------------------------------------

                st.session_state.order_id = order_id.strip()

                st.session_state.order_date = (
                    order_date.strip() or None
                )

                st.session_state.product_name = (
                    product_name.strip()
                )

                st.session_state.product_category = (
                    product_category.strip()
                )

                st.session_state.customer_name = (
                    customer_name.strip()
                )

                st.session_state.company_name = (
                    company_name.strip()
                )

                st.session_state.purchase_price = (
                    float(purchase_price)
                )

                st.session_state.quantity = int(quantity)

                st.session_state.currency = currency.strip()

                st.session_state.delivery_status = (
                    delivery_status
                )

                st.session_state.delivery_date = (
                    delivery_date.strip() or None
                )

                st.session_state.stamp_detected = (
                    bool(stamp_detected)
                )

                st.session_state.description = description.strip()

                st.session_state.order_extraction = extraction

                # ---------------------------------------------
                # SAVE PRODUCT IMAGE
                # ---------------------------------------------

                image_bytes = uploaded_image.getvalue()

                st.session_state.image_bytes = image_bytes

                st.session_state.image_mime_type = (
                    uploaded_image.type
                )

                # ---------------------------------------------
                # RESET PREVIOUS VISION RESULTS
                # ---------------------------------------------

                st.session_state.pop(
                    "vision_result",
                    None,
                )

                st.session_state.pop(
                    "vision_agent_state",
                    None,
                )

                # ---------------------------------------------
                # NAVIGATE TO AI ANALYSIS
                # ---------------------------------------------

                st.session_state.page = "AI Analysis"

                st.rerun()

    # =========================================================
    # INFORMATION
    # =========================================================

    st.write("")

    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:

        st.caption("SECURE")

        st.write(
            "Review the extracted information before submitting "
            "your return claim."
        )

    with col2:

        st.caption("MULTIMODAL")

        st.write(
            "Gemini extracts information from the order document "
            "and separately analyzes the product photo."
        )

    with col3:

        st.caption("HUMAN REVIEW")

        st.write(
            "Uncertain extractions and suspicious inconsistencies "
            "should be reviewed before a return decision."
        )
