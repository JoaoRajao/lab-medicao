from __future__ import annotations

from datetime import date
from typing import Any


def calculate_invoice(invoice: dict[str, Any], paid_at: str) -> dict[str, Any]:
    paid_date = date.fromisoformat(paid_at)
    due_date = date.fromisoformat(invoice["due_at"])
    days_delta = (paid_date - due_date).days

    amount = float(invoice["amount"])
    if days_delta < 0:
        status = "early"
        amount *= 1 - float(invoice["early_discount_pct"]) / 100
    elif days_delta > 0:
        status = "late"
        amount *= 1 + float(invoice["late_fee_pct"]) / 100
    else:
        status = "on_time"

    return {
        "status": status,
        "final_amount": round(amount, 2),
        "days_delta": days_delta,
    }
