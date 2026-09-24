from __future__ import annotations

from typing import Any


def consolidate_batches(batches: list[dict[str, Any]], today: str) -> list[dict[str, Any]]:
    consolidated: dict[str, dict[str, Any]] = {}

    for batch in batches:
        if batch["expires_at"] < today:
            continue

        sku = batch["sku"]
        if sku not in consolidated:
            consolidated[sku] = {
                "sku": sku,
                "quantity": 0,
                "next_expiration": batch["expires_at"],
                "max_priority": batch["priority"],
            }

        item = consolidated[sku]
        item["quantity"] += batch["quantity"]
        item["next_expiration"] = min(item["next_expiration"], batch["expires_at"])
        item["max_priority"] = max(item["max_priority"], batch["priority"])

    return sorted(consolidated.values(), key=lambda item: (item["next_expiration"], item["sku"]))
