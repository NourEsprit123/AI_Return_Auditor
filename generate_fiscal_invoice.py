"""
generate_fiscal_invoice.py
==========================

Generates two digital PDF invoices for stress-testing test_cachet_fiscal.py:

  invoice_with_fiscal_stamp.pdf    — carries an official-looking fiscal stamp
  invoice_without_fiscal_stamp.pdf — identical layout, stamp area left blank

Dependencies : reportlab (already in requirements.txt)
Usage        : python generate_fiscal_invoice.py
"""

from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parent
OUT_WITH    = ROOT / "invoice_with_fiscal_stamp.pdf"
OUT_WITHOUT = ROOT / "invoice_without_fiscal_stamp.pdf"


# ============================================================
# SHARED INVOICE DATA
# ============================================================

COMPANY     = "TechShop Europe SARL"
ADDRESS     = "12 Rue de l'Innovation, 75008 Paris, France"
VAT_NUMBER  = "FR 12 345678901"
CLIENT      = "Jean Dupont — 8 Avenue des Lilas, 69003 Lyon"
ORDER_ID    = "Order #58291"
PRODUCT     = "Ergonomic Office Chair"
UNIT_PRICE  = 189.99
QTY         = 2
TAX_RATE    = 0.20


# ============================================================
# CORE BUILDER
# ============================================================

def build_invoice(output_path: Path, include_stamp: bool) -> None:
    """
    Draw a clean A4 invoice and optionally append a fiscal stamp block.

    Parameters
    ----------
    output_path  : destination PDF path
    include_stamp: True  → draw the fiscal stamp rectangle + text
                   False → leave the stamp area completely blank
    """
    c = canvas.Canvas(str(output_path), pagesize=A4)
    W, H = A4  # 595 x 842 pt

    LEFT  = 50
    RIGHT = W - 50

    # ── Helper: horizontal rule ───────────────────────────────
    def hline(y: float, width: float = 0.5) -> None:
        c.setLineWidth(width)
        c.line(LEFT, y, RIGHT, y)

    # ── Header band ───────────────────────────────────────────
    c.setFillColorRGB(0.08, 0.08, 0.38)
    c.rect(0, H - 72, W, 72, fill=1, stroke=0)

    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(LEFT, H - 36, COMPANY)

    c.setFont("Helvetica", 8)
    c.drawString(LEFT, H - 50, ADDRESS)
    c.drawString(LEFT, H - 62, f"VAT: {VAT_NUMBER}")

    # ── Document title ────────────────────────────────────────
    c.setFillColorRGB(0.08, 0.08, 0.38)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W / 2, H - 100, "INVOICE")

    c.setStrokeColorRGB(0.08, 0.08, 0.38)
    c.setLineWidth(1.2)
    hline(H - 110, 1.2)

    # ── Metadata block ────────────────────────────────────────
    c.setFillColorRGB(0.15, 0.15, 0.15)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(LEFT, H - 130, "Bill to:")
    c.setFont("Helvetica", 9)
    c.drawString(LEFT, H - 143, CLIENT)

    c.setFont("Helvetica-Bold", 9)
    c.drawString(LEFT, H - 163, f"Order reference : {ORDER_ID}")
    c.setFont("Helvetica", 9)
    c.drawString(LEFT, H - 176, "Date: 14 October 2026")

    hline(H - 186, 0.5)

    # ── Table header ──────────────────────────────────────────
    c.setFillColorRGB(0.90, 0.90, 0.95)
    c.rect(LEFT, H - 210, RIGHT - LEFT, 20, fill=1, stroke=0)

    c.setFillColorRGB(0.08, 0.08, 0.38)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(LEFT + 4,  H - 203, "Description")
    c.drawString(340,        H - 203, "Qty")
    c.drawString(400,        H - 203, "Unit Price")
    c.drawString(490,        H - 203, "Line Total")

    # ── Item row ──────────────────────────────────────────────
    line_total  = round(UNIT_PRICE * QTY, 2)
    subtotal    = line_total
    tax_amount  = round(subtotal * TAX_RATE, 2)
    grand_total = round(subtotal + tax_amount, 2)

    c.setFillColorRGB(0.15, 0.15, 0.15)
    c.setFont("Helvetica", 9)
    c.drawString(LEFT + 4,  H - 224, f"Item: {PRODUCT}")
    c.drawString(346,        H - 224, str(QTY))
    c.drawString(400,        H - 224, f"{UNIT_PRICE:.2f} EUR")
    c.drawString(490,        H - 224, f"{line_total:.2f} EUR")

    hline(H - 234, 0.5)

    # ── Totals block ──────────────────────────────────────────
    c.setFont("Helvetica", 9)
    c.drawString(370, H - 250, "Subtotal:")
    c.drawString(490, H - 250, f"{subtotal:.2f} EUR")

    c.drawString(370, H - 264, f"VAT ({int(TAX_RATE*100)}%):")
    c.drawString(490, H - 264, f"{tax_amount:.2f} EUR")

    hline(H - 272, 0.8)

    c.setFont("Helvetica-Bold", 10)
    c.drawString(370, H - 286, "Total:")
    c.drawString(490, H - 286, f"{grand_total:.2f} EUR")

    hline(H - 294, 0.5)

    # ── Payment info ──────────────────────────────────────────
    c.setFont("Helvetica-Bold", 9)
    c.drawString(LEFT, H - 314, "Payment method:")
    c.setFont("Helvetica", 9)
    c.drawString(LEFT, H - 327, "Bank Transfer — IBAN FR76 1234 5678 9012 3456 7890 123")

    # ── Legal note ────────────────────────────────────────────
    c.setFont("Helvetica-Oblique", 7)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawString(LEFT, H - 355,
        "Pursuant to Article 289 of the French General Tax Code, this invoice "
        "constitutes a legally binding fiscal document.")

    # ============================================================
    # FISCAL STAMP — bottom-right corner
    # Drawn only when include_stamp=True; area is blank otherwise.
    # ============================================================

    STAMP_X = RIGHT - 210   # left edge of stamp box
    STAMP_Y = 42            # bottom edge
    STAMP_W = 200
    STAMP_H = 52

    if include_stamp:
        # Outer border — dark blue rectangle
        c.setStrokeColorRGB(0.05, 0.20, 0.55)
        c.setLineWidth(2.0)
        c.rect(STAMP_X, STAMP_Y, STAMP_W, STAMP_H, fill=0, stroke=1)

        # Inner fill — very light blue tint
        c.setFillColorRGB(0.93, 0.95, 1.0)
        c.rect(STAMP_X + 2, STAMP_Y + 2, STAMP_W - 4, STAMP_H - 4, fill=1, stroke=0)

        # Stamp label — line 1
        c.setFillColorRGB(0.05, 0.20, 0.55)
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(
            STAMP_X + STAMP_W / 2,
            STAMP_Y + STAMP_H - 14,
            "STATE TAX AUTHORITY",
        )

        # Stamp label — line 2
        c.setFont("Helvetica-Bold", 6.5)
        c.drawCentredString(
            STAMP_X + STAMP_W / 2,
            STAMP_Y + STAMP_H - 26,
            "OFFICIAL FISCAL STAMP",
        )

        # Reference number
        c.setFont("Helvetica", 6)
        c.drawCentredString(
            STAMP_X + STAMP_W / 2,
            STAMP_Y + STAMP_H - 38,
            "Ref. FISC-2026-058291",
        )

        # Bottom date line
        c.setFont("Helvetica-Oblique", 6)
        c.drawCentredString(
            STAMP_X + STAMP_W / 2,
            STAMP_Y + 8,
            "Validated: 14/10/2026",
        )

    # ── Footer band ───────────────────────────────────────────
    c.setFillColorRGB(0.08, 0.08, 0.38)
    c.rect(0, 0, W, 36, fill=1, stroke=0)

    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica", 7)
    c.drawCentredString(W / 2, 22,
        "TechShop Europe SARL — Capital 50,000 EUR — RCS Paris B 123 456 789")
    c.drawCentredString(W / 2, 12,
        "Computer-generated document — www.techshop-europe.com")

    c.save()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    variants = [
        (OUT_WITH,    True,  "WITH fiscal stamp"),
        (OUT_WITHOUT, False, "WITHOUT fiscal stamp"),
    ]

    print("=" * 52)
    print("  FISCAL INVOICE GENERATOR")
    print("=" * 52)

    for path, stamp, label in variants:
        build_invoice(path, include_stamp=stamp)
        status = "✓" if path.exists() else "✗"
        print(f"  {status}  {label:<26}  →  {path.name}")

    print("=" * 52)
    print("  Feed these files into test_cachet_fiscal.py")
    print(f"  Port: streamlit run test_cachet_fiscal.py --server.port 8510")
    print("=" * 52)
