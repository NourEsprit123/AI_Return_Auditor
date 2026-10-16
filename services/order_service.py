"""
services/order_service.py
-------------------------
Order lookup service.

Reads order information from data/orders.csv and returns
a structured OrderInfo dict for use by Agent 3.
"""

from pathlib import Path
from typing import Optional

import pandas as pd


# ============================================================
# PATHS
# ============================================================

ORDERS_CSV = (
    Path(__file__).resolve().parent.parent / "data" / "orders.csv"
)


# ============================================================
# ORDER INFO SCHEMA
# ============================================================

def empty_order(order_id: str) -> dict:
    """Return a safe default when an order is not found."""
    return {
        "order_id":            order_id,
        "customer_name":       "Unknown",
        "product_name":        "Unknown",
        "product_category":    "Unknown",
        "purchase_price":      0.0,
        "order_date":          "Unknown",
        "delivery_date":       "Unknown",
        "delivery_status":     "Unknown",
        "days_since_delivery": -1,
        "return_window_days":  30,
        "within_return_window": False,
        "found":               False,
    }


# ============================================================
# LOOKUP
# ============================================================

def get_order(order_id: str) -> dict:
    """
    Look up an order by ID from orders.csv.

    Parameters
    ----------
    order_id : The order ID string (e.g. 'ORD-003').

    Returns
    -------
    Dict with order fields. Includes 'found': True/False.
    """

    if not ORDERS_CSV.exists():
        print(f"[OrderService] orders.csv not found: {ORDERS_CSV}")
        return empty_order(order_id)

    try:
        df = pd.read_csv(ORDERS_CSV)

        # Normalise: strip whitespace from order_id column
        df["order_id"] = df["order_id"].astype(str).str.strip()
        order_id_clean = str(order_id).strip()

        row = df[df["order_id"] == order_id_clean]

        if row.empty:
            print(f"[OrderService] Order not found: {order_id}")
            return empty_order(order_id)

        r = row.iloc[0]

        return {
            "order_id":            str(r["order_id"]),
            "customer_name":       str(r.get("customer_name", "Unknown")),
            "product_name":        str(r.get("product_name", "Unknown")),
            "product_category":    str(r.get("product_category", "Unknown")),
            "purchase_price":      float(r.get("purchase_price", 0.0)),
            "order_date":          str(r.get("order_date", "Unknown")),
            "delivery_date":       str(r.get("delivery_date", "Unknown")),
            "delivery_status":     str(r.get("delivery_status", "Unknown")),
            "days_since_delivery": int(r.get("days_since_delivery", -1)),
            "return_window_days":  int(r.get("return_window_days", 30)),
            "within_return_window": bool(r.get("within_return_window", False)),
            "found":               True,
        }

    except Exception as exc:
        print(f"[OrderService] Error reading orders.csv: {exc}")
        return empty_order(order_id)


def build_order_from_session(session: dict) -> dict:
    """
    Build an order info dict directly from Streamlit session state
    when no order ID is matched in the CSV.

    Used as a fallback so the pipeline always has order data.
    """

    price = float(session.get("purchase_price", 0.0))
    delivery_status = str(session.get("delivery_status", "Delivered"))

    # Estimate return window eligibility from session
    # (we don't have the actual delivery date in session,
    #  so we assume delivered and within window unless status says otherwise)
    within_window = delivery_status == "Delivered"

    return {
        "order_id":            str(session.get("order_id", "Unknown")),
        "customer_name":       "Customer",
        "product_name":        str(session.get("product_name", "Unknown")),
        "product_category":    str(session.get("product_category", "Unknown")),
        "purchase_price":      price,
        "order_date":          "Unknown",
        "delivery_date":       "Unknown",
        "delivery_status":     delivery_status,
        "days_since_delivery": -1,
        "return_window_days":  30,
        "within_return_window": within_window,
        "found":               False,
    }
