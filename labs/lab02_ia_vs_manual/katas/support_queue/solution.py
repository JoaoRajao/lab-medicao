from __future__ import annotations

from typing import Any

SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def prioritize_tickets(tickets: list[dict[str, Any]]) -> list[str]:
    def sort_key(ticket: dict[str, Any]) -> tuple[int, int, int, int]:
        overdue = ticket["minutes_to_sla"] < 0
        return (
            0 if overdue else 1,
            SEVERITY_RANK[ticket["severity"]],
            ticket["minutes_to_sla"],
            ticket["created_seq"],
        )

    ordered = sorted(tickets, key=sort_key)
    return [ticket["id"] for ticket in ordered]