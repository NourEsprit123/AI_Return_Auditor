"""
generate_sample_receipt.py
==========================

Mock e-commerce invoice generator.
Produces a randomized digital PDF receipt at the project root as
`sample_ecom_receipt.pdf`, ready to stress-test test_receipt_extractor.py.

Dependencies : reportlab (pip install reportlab)
Usage        : python generate_sample_receipt.py
"""

import random
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


# ============================================================
# CONFIGURATION
# ============================================================

OUTPUT_PATH = Path(__file__).resolve().parent / "sample_ecom_receipt.pdf"

PRODUCT_CATALOGUE = [
    "Wireless Headphones",
    "Mechanical Keyboard",
    "USB-C Hub",
    "4K Webcam",
    "Noise-Cancelling Earbuds",
    "Portable SSD 1TB",
    "Smart LED Desk Lamp",
    "Ergonomic Mouse",
    "27-inch Monitor",
    "Laptop Stand",
]

COMPANY_NAME = "TechShop Europe"
COMPANY_ADDRESS = "12 Rue de l'Innovation, 75008 Paris, France"
COMPANY_EMAIL = "support@techshop-europe.com"
COMPANY_VAT = "FR 12 345678901"


# ============================================================
# RANDOM DATA GENERATION
# ============================================================

def generate_order_id() -> str:
    """Return either 'Order #NNNNN' or 'ID-NNNNN' at random."""
    number = random.randint(10000, 99999)
    prefix = random.choice(["Order #", "ID-"])
    return f"{prefix}{number}"


def generate_product() -> str:
    """Pick a random product from the catalogue."""
    return random.choice(PRODUCT_CATALOGUE)


def generate_price() -> float:
    """Random price between 20.00 and 150.00, rounded to 2 decimal places."""
    return round(random.uniform(20.00, 150.00), 2)


def generate_quantity() -> int:
    return random.randint(1, 3)


# ============================================================
# PDF DRAWING
# ============================================================

def build_receipt(order_id: str, product: str, price: float, qty: int) -> None:
    """
    Draw a clean corporate receipt onto an A4 canvas and save it.

    Text layout uses explicit y-coordinates so that pdfplumber extracts
    each field on its own line — no multi-column layout that could merge
    tokens during text extraction.
    """
    c = canvas.Canvas(str(OUTPUT_PATH), pagesize=A4)
    width, height = A4  # 595 x 842 pt

    # ── Helpers ─────────────────────────────────────────────
    LEFT = 60
    RIGHT = width - 60

    def line(y: float) -> None:
        """Draw a horizontal rule."""
        c.line(LEFT, y, RIGHT, y)

    # ── Header band ─────────────────────────────────────────
    c.setFillColorRGB(0.10, 0.10, 0.40)          # dark navy
    c.rect(0, height - 70, width, 70, fill=1, stroke=0)

    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(LEFT, height - 38, COMPANY_NAME)

    c.setFont("Helvetica", 9)
    c.drawString(LEFT, height - 54, COMPANY_ADDRESS)
    c.drawString(LEFT, height - 65, f"Email: {COMPANY_EMAIL}  |  VAT: {COMPANY_VAT}")

    # ── Title ───────────────────────────────────────────────
    c.setFillColorRGB(0.10, 0.10, 0.40)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 110, "SALES RECEIPT")

    # ── Divider ─────────────────────────────────────────────
    c.setStrokeColorRGB(0.10, 0.10, 0.40)
    c.setLineWidth(1.2)
    line(height - 120)

    # ── Order metadata block ─────────────────────────────────
    # Each field is on its own line with a clear "Keyword: value" format
    # so the regex parser in test_receipt_extractor.py matches cleanly.
    c.setFillColorRGB(0.15, 0.15, 0.15)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(LEFT, height - 145, "Order Reference")

    c.setFont("Helvetica", 10)
    c.drawString(LEFT, height - 160, f"Order: {order_id}")

    # Date (static label, not parsed — adds realism)
    import datetime
    today = datetime.date.today().strftime("%d %B %Y")
    c.drawString(LEFT, height - 175, f"Date: {today}")

    # ── Divider ─────────────────────────────────────────────
    c.setLineWidth(0.5)
    line(height - 185)

    # ── Items table header ───────────────────────────────────
    c.setFillColorRGB(0.92, 0.92, 0.96)
    c.rect(LEFT, height - 215, RIGHT - LEFT, 22, fill=1, stroke=0)

    c.setFillColorRGB(0.10, 0.10, 0.40)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(LEFT + 4, height - 207, "Description")
    c.drawString(350, height - 207, "Qty")
    c.drawString(430, height - 207, "Unit Price")
    c.drawString(510, height - 207, "Amount")

    # ── Item row ─────────────────────────────────────────────
    unit_price = price
    total_line = round(unit_price * qty, 2)

    c.setFillColorRGB(0.15, 0.15, 0.15)
    c.setFont("Helvetica", 10)

    # "Description:" prefix ensures _PATTERN_PRODUCT regex fires
    c.drawString(LEFT + 4, height - 235, f"Description: {product}")
    c.drawString(358, height - 235, str(qty))
    c.drawString(430, height - 235, f"{unit_price:.2f}")
    c.drawString(510, height - 235, f"{total_line:.2f}")

    # ── Subtotals block ───────────────────────────────────────
    line(height - 248)

    TAX_RATE = 0.20
    subtotal = total_line
    tax = round(subtotal * TAX_RATE, 2)
    grand_total = round(subtotal + tax, 2)

    c.setFont("Helvetica", 10)
    c.drawString(380, height - 265, "Subtotal:")
    c.drawString(510, height - 265, f"{subtotal:.2f} EUR")

    c.drawString(380, height - 280, "VAT (20%):")
    c.drawString(510, height - 280, f"{tax:.2f} EUR")

    c.setLineWidth(1.0)
    line(height - 288)

    # "Total:" prefix is the key anchor for _PATTERN_PRICE regex
    c.setFont("Helvetica-Bold", 11)
    c.drawString(380, height - 303, "Total:")
    c.drawString(510, height - 303, f"{grand_total:.2f} USD")

    # Also emit a secondary "Price:" line for redundancy testing
    c.setFont("Helvetica", 9)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawString(380, height - 318, f"Price: {grand_total:.2f}")

    # ── Payment info ─────────────────────────────────────────
    line(height - 330)
    c.setFillColorRGB(0.15, 0.15, 0.15)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(LEFT, height - 348, "Payment Method:")
    c.setFont("Helvetica", 10)
    c.drawString(LEFT, height - 363, random.choice(["Credit Card", "PayPal", "Bank Transfer"]))

    # ── Footer ───────────────────────────────────────────────
    c.setFillColorRGB(0.10, 0.10, 0.40)
    c.rect(0, 0, width, 40, fill=1, stroke=0)

    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica", 8)
    c.drawCentredString(
        width / 2, 25,
        "Thank you for your purchase — For returns visit: www.techshop-europe.com/returns"
    )
    c.drawCentredString(width / 2, 14, "This is a computer-generated receipt. No signature required.")

    c.save()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    order_id = generate_order_id()
    product  = generate_product()
    price    = generate_price()
    qty      = generate_quantity()

    build_receipt(order_id, product, price, qty)

    print("=" * 48)
    print("  SAMPLE RECEIPT GENERATED")
    print("=" * 48)
    print(f"  Order ID      : {order_id}")
    print(f"  Product       : {product}")
    print(f"  Unit Price    : {price:.2f} USD")
    print(f"  Quantity      : {qty}")
    print(f"  Grand Total   : {round(price * qty * 1.20, 2):.2f} USD  (incl. 20% VAT)")
    print(f"  Saved to      : {OUTPUT_PATH}")
    print("=" * 48)
