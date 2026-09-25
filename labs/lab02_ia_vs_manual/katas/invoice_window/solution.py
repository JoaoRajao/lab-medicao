from __future__ import annotations

from datetime import date
from typing import Any


def calculate_invoice(invoice: dict[str, Any], paid_at: str) -> dict[str, Any]:
    due = date.fromisoformat(invoice["due_at"])
    paid = date.fromisoformat(paid_at)
    days_delta = (paid - due).days

    amount = invoice["amount"]
    if days_delta < 0:
        status = "early"
        final_amount = amount * (1 - invoice["early_discount_pct"] / 100)
    elif days_delta == 0:
        status = "on_time"
        final_amount = amount
    else:
        status = "late"
        final_amount = amount * (1 + invoice["late_fee_pct"] / 100)

    return {
        "status": status,
        "final_amount": round(final_amount, 2),
        "days_delta": days_delta,
    }