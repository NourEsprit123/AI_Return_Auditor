"""
agents/document_agent.py
-------------------------
Document Extraction Agent

Extracts structured order/warranty information from an uploaded
document (PDF, image of receipt, warranty card, invoice).

Uses Gemini multimodal to read the document and extract:
- order_id
- product_name
- product_category
- purchase_price
- purchase_date
- store / vendor name

If the document does not contain recognizable purchase information,
the agent returns an empty result with a clear message so the user
can fill the form manually.
"""

import os
import io
import time
from pathlib import Path
from typing import Optional

os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

from dotenv import load_dotenv
from google import genai
from PIL import Image
from pydantic import BaseModel, Field

load_dotenv()

API_KEY   = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("GEMINI_VISION_MODEL", "gemini-3.1-flash-lite")


# ============================================================
# PDF → IMAGE CONVERSION
# ============================================================

def pdf_to_image(pdf_bytes: bytes) -> Image.Image:
    """
    Convert the first page of a PDF to a PIL Image using PyMuPDF.
    Falls back gracefully if conversion fails.
    """
    import pymupdf as fitz  # PyMuPDF (new import style)

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[0]

    # Render at 2x resolution for better OCR quality
    mat = fitz.Matrix(2.0, 2.0)
    pix = page.get_pixmap(matrix=mat)
    doc.close()

    # Convert pixmap to PIL Image
    img_bytes = pix.tobytes("png")
    image = Image.open(io.BytesIO(img_bytes)).convert("RGB")

    return image


# ============================================================
# STRUCTURED OUTPUT
# ============================================================

class DocumentExtraction(BaseModel):
    """
    Fields extracted from a warranty card, receipt, or invoice.
    Any field that could not be found is returned as an empty string.
    """

    order_id: str = Field(
        default="",
        description="Order number, invoice number, or reference ID. Empty if not found."
    )
    product_name: str = Field(
        default="",
        description="Product name or model. Empty if not found."
    )
    product_category: str = Field(
        default="",
        description=(
            "Product category. One of: Footwear, Clothing, Electronics, "
            "Home & Kitchen, Beauty, Accessories, Other. Empty if not found."
        )
    )
    purchase_price: str = Field(
        default="",
        description="Purchase price as a number string. Empty if not found."
    )
    purchase_date: str = Field(
        default="",
        description="Purchase date in any format found in the document. Empty if not found."
    )
    store_name: str = Field(
        default="",
        description="Store or vendor name. Empty if not found."
    )
    extraction_successful: bool = Field(
        default=False,
        description=(
            "True if at least product_name or order_id was successfully extracted. "
            "False if the document does not appear to be a valid purchase document."
        )
    )
    extraction_notes: str = Field(
        default="",
        description=(
            "Brief note about extraction quality or reason for failure."
        )
    )


# ============================================================
# DOCUMENT AGENT
# ============================================================

class DocumentAgent:
    """
    Extracts purchase/warranty information from uploaded documents.
    """

    PROMPT = """
You are a document information extraction assistant for an e-commerce return system.

Your task is to extract purchase and product information from the uploaded document.
The document may be a warranty card, purchase receipt, invoice, or order confirmation.

Extract the following fields if present:
- Order ID / Invoice number / Reference number
- Product name or model
- Product category (Footwear, Clothing, Electronics, Home & Kitchen, Beauty, Accessories, Other)
- Purchase price (number only, no currency symbol)
- Purchase date
- Store or vendor name

Rules:
- Only extract information that is clearly visible in the document.
- Do NOT invent or guess information.
- If the document is not a purchase document (e.g. it's a random photo, ID card, or unrelated paper),
  set extraction_successful to false and explain in extraction_notes.
- If you find at least the product name or order ID, set extraction_successful to true.
- Keep extraction_notes brief (1 sentence).

Return only the structured DocumentExtraction result.
"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or API_KEY
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")
        self.client = genai.Client(api_key=self.api_key)

    def extract(self, image_or_bytes, is_pdf: bool = False) -> DocumentExtraction:
        """
        Extract purchase information from a document.

        Parameters
        ----------
        image_or_bytes : PIL Image or raw bytes (PDF).
        is_pdf         : True if the input is PDF bytes.

        Returns
        -------
        DocumentExtraction with extracted fields.
        """

        # Convert PDF to image if needed
        if is_pdf:
            try:
                image = pdf_to_image(image_or_bytes)
                print("[DocumentAgent] PDF converted to image successfully.")
            except Exception as exc:
                print(f"[DocumentAgent] PDF conversion failed: {exc}")
                return DocumentExtraction(
                    extraction_successful=False,
                    extraction_notes=f"Could not read the PDF file: {exc}. Please upload an image instead.",
                )
        else:
            image = image_or_bytes

        models_to_try = [
            MODEL_NAME,
            "gemini-3.1-flash-lite",
            "gemini-3.5-flash",
            "gemini-3.6-flash",
        ]
        models_to_try = list(dict.fromkeys(models_to_try))

        for model_name in models_to_try:

            for attempt in range(2):

                try:

                    print(f"[DocumentAgent] Extracting | Model: {model_name}")

                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=[self.PROMPT, image],
                        config={
                            "response_mime_type": "application/json",
                            "response_schema": DocumentExtraction,
                        },
                    )

                    if getattr(response, "parsed", None):
                        result = response.parsed
                        print(
                            f"[DocumentAgent] Extracted: "
                            f"product={result.product_name}, "
                            f"success={result.extraction_successful}"
                        )
                        return result

                    if getattr(response, "text", None):
                        return DocumentExtraction.model_validate_json(response.text)

                except Exception as exc:
                    error_text = str(exc).lower()
                    is_temp = any(x in error_text for x in ["503", "unavailable", "429", "high demand"])
                    if is_temp and attempt == 0:
                        print(f"[DocumentAgent] Temporary error, retrying...")
                        time.sleep(3)
                        continue
                    print(f"[DocumentAgent] Model {model_name} failed: {exc}")
                    break

        # All models failed
        return DocumentExtraction(
            extraction_successful=False,
            extraction_notes="Could not analyze the document. Please fill the form manually.",
        )
