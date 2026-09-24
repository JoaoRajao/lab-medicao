from __future__ import annotations

from typing import Any


def prioritize_tickets(tickets: list[dict[str, Any]]) -> list[str]:
    severity_rank = {
        "critical": 0,
        "high": 1,
        "medium": 2,
        "low": 3,
    }

    def sort_key(ticket: dict[str, Any]) -> tuple[bool, int, int, int]:
        return (
            ticket["minutes_to_sla"] >= 0,
            severity_rank[ticket["severity"]],
            ticket["minutes_to_sla"],
            ticket["created_seq"],
        )

    return [ticket["id"] for ticket in sorted(tickets, key=sort_key)]
