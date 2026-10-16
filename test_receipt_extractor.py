"""
Receipt Extractor — Proof of Concept (POC)
==========================================

Standalone script to automate the "Return Request" form by extracting
structured data from a digital PDF receipt.

Approach
--------
- Pure text extraction via pdfplumber (no neural network, no OCR).
- Works on digital PDFs only (not scanned images).
- Regex-based field mapping → clean payload dict ready for the pipeline.

Architectural isolation
-----------------------
No imports from agents/, components/, views/, services/, or rag/.
This file is fully self-contained.

Branch : feature/detection-cachet-fiscal
"""

import io
import re
from typing import Optional

import pdfplumber


# ============================================================
# REGEX PATTERNS
# ============================================================

# Matches: "Order #12345", "Order: 12345", "ID: 56789", "ID #56789"
_PATTERN_ORDER_ID = re.compile(
    r"(?:Order\s*[#:]?\s*#?|ID\s*[:#]?\s*)(\d{4,})",
    re.IGNORECASE,
)

# Matches: "Item: ...", "Product: ...", "Description: ..."
# Captures the product name up to the first digit (qty / price column)
# so that table rows like "Description: USB-C Hub 3 142.97" don't bleed
# the numeric columns into the product name.
_PATTERN_PRODUCT = re.compile(
    r"(?:Item|Product|Description)\s*[:#]\s*([^\d\n]+?)(?=\s+\d|\s*$)",
    re.IGNORECASE,
)

# Matches: "Total: $49.99", "Price: 120,00", "Amount: 9.90"
# Accepts both dot and comma as decimal separator.
_PATTERN_PRICE = re.compile(
    r"(?:Total|Price|Amount|Unit\s*Price)\s*[:#]?\s*\$?\s*([\d]+(?:[.,]\d{1,2})?)",
    re.IGNORECASE,
)


# ============================================================
# BLOC 1 — PDF TEXT EXTRACTION
# ============================================================

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract all raw text from a digital PDF document.

    Parameters
    ----------
    file_bytes : bytes
        Raw bytes of the PDF file (from st.file_uploader or open()).

    Returns
    -------
    str
        Concatenated plain text from all pages, separated by newlines.
        Returns an empty string if no text layer is found.

    Notes
    -----
    This function works on digital (text-layer) PDFs only.
    Scanned image-based PDFs will return an empty string because
    pdfplumber cannot perform OCR.
    """
    pages_text: list[str] = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                pages_text.append(page_text)

    return "\n".join(pages_text)


# ============================================================
# BLOC 2 — PAYLOAD PARSING
# ============================================================

def parse_receipt(raw_text: str) -> dict:
    """
    Map raw extracted text to a structured payload dict.

    The payload keys align with the Return Request form fields:
        - order_id       : str  | None
        - product_name   : str  | None
        - purchase_price : float | None

    Behaviour on multiple matches
    ------------------------------
    Only the first match for each field is kept.
    This is intentional: on a standard receipt the first occurrence
    of "Total" or "Order #" is the relevant one.

    Parameters
    ----------
    raw_text : str
        Plain text output of extract_text_from_pdf().

    Returns
    -------
    dict
        {"order_id": ..., "product_name": ..., "purchase_price": ...}
        Missing fields are represented as None (not omitted).
    """

    # --- order_id ---
    order_id: Optional[str] = None
    match_order = _PATTERN_ORDER_ID.search(raw_text)
    if match_order:
        order_id = match_order.group(1).strip()

    # --- product_name ---
    product_name: Optional[str] = None
    match_product = _PATTERN_PRODUCT.search(raw_text)
    if match_product:
        product_name = match_product.group(1).strip()

    # --- purchase_price ---
    purchase_price: Optional[float] = None
    match_price = _PATTERN_PRICE.search(raw_text)
    if match_price:
        # Normalize decimal separator: comma → dot
        raw_price = match_price.group(1).replace(",", ".")
        try:
            purchase_price = float(raw_price)
        except ValueError:
            purchase_price = None

    return {
        "order_id": order_id,
        "product_name": product_name,
        "purchase_price": purchase_price,
    }


# ============================================================
# BLOC 3 — STREAMLIT UI
# ============================================================

if __name__ == "__main__":

    import base64
    import streamlit as st

    st.set_page_config(
        page_title="AI Return Auditor - Receipt Parser POC",
        page_icon="🧾",
        layout="wide",
    )

    st.title("🧾 AI Return Auditor — Receipt Parser POC")
    st.caption(
        "Automated extraction of return request parameters from a digital PDF receipt."
    )

    st.markdown(
        "Upload a **digital PDF receipt** to automatically populate the "
        "Return Request payload. "
        "Scanned (image-only) PDFs are not supported by this POC."
    )

    st.divider()

    uploaded_pdf = st.file_uploader(
        "Upload a PDF receipt",
        type=["pdf"],
        help="Digital PDFs only — text layer required.",
    )

    if uploaded_pdf is not None:

        file_bytes = uploaded_pdf.read()

        with st.spinner("Extracting text from PDF..."):
            raw_text = extract_text_from_pdf(file_bytes)

        # ── Guard: empty extraction ──────────────────────────────
        if not raw_text.strip():
            st.warning(
                "⚠️ No text layer found in this PDF. "
                "This POC supports digital PDFs only. "
                "Scanned receipts require an OCR step (out of scope here).",
                icon="⚠️",
            )
            st.stop()

        # ── PDF preview (full width) ──────────────────────────────
        st.subheader("📑 PDF Preview")
        base64_pdf = base64.b64encode(file_bytes).decode("utf-8")
        pdf_display = (
            f'<iframe src="data:application/pdf;base64,{base64_pdf}" '
            f'width="100%" height="600" type="application/pdf"></iframe>'
        )
        st.markdown(pdf_display, unsafe_allow_html=True)

        st.divider()

        # ── Structured payload ────────────────────────────────────
        with st.spinner("Parsing receipt fields..."):
            payload = parse_receipt(raw_text)

        st.subheader("🗂️ Structured Payload")
        st.caption(
            "Ready to feed into the Return Request pipeline."
        )
        st.json(payload)

        # ── Field coverage feedback ───────────────────────────────
        missing = [k for k, v in payload.items() if v is None]

        if not missing:
            st.success(
                "All fields extracted successfully.",
                icon="✅",
            )
        else:
            st.warning(
                f"Could not extract the following field(s): "
                f"`{'`, `'.join(missing)}`. "
                "Check that the PDF contains standard keywords "
                "(Order #, Item:, Total:).",
                icon="⚠️",
            )

        st.divider()

        # ── Raw text ──────────────────────────────────────────────
        with st.expander("📄 Raw Extracted Text"):
            st.code(raw_text, language=None)

    else:
        st.info(
            "Upload a PDF receipt above to start the extraction.",
            icon="⬆️",
        )

    st.divider()
    st.caption("Extraction engine: pdfplumber · No neural network · No OCR")
