from __future__ import annotations

from datetime import date
from typing import Any


def consolidate_batches(batches: list[dict[str, Any]], today: str) -> list[dict[str, Any]]:
    today_date = date.fromisoformat(today)
    groups: dict[str, dict[str, Any]] = {}

    for batch in batches:
        if date.fromisoformat(batch["expires_at"]) < today_date:
            continue
        sku = batch["sku"]
        if sku not in groups:
            groups[sku] = {
                "sku": sku,
                "quantity": 0,
                "next_expiration": batch["expires_at"],
                "max_priority": batch["priority"],
            }
        group = groups[sku]
        group["quantity"] += batch["quantity"]
        group["next_expiration"] = min(group["next_expiration"], batch["expires_at"])
        group["max_priority"] = max(group["max_priority"], batch["priority"])

    return sorted(groups.values(), key=lambda g: (g["next_expiration"], g["sku"]))
