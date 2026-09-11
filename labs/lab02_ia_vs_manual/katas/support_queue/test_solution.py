from labs.lab02_ia_vs_manual.katas.support_queue.solution import prioritize_tickets


def test_prioritizes_overdue_and_severity() -> None:
    tickets = [
        {"id": "T1", "severity": "medium", "minutes_to_sla": 30, "created_seq": 1},
        {"id": "T2", "severity": "low", "minutes_to_sla": -5, "created_seq": 2},
        {"id": "T3", "severity": "critical", "minutes_to_sla": 80, "created_seq": 3},
        {"id": "T4", "severity": "high", "minutes_to_sla": -2, "created_seq": 4},
    ]

    assert prioritize_tickets(tickets) == ["T4", "T2", "T3", "T1"]


def test_uses_sla_then_creation_as_tie_breakers() -> None:
    tickets = [
        {"id": "A", "severity": "high", "minutes_to_sla": 20, "created_seq": 2},
        {"id": "B", "severity": "high", "minutes_to_sla": 10, "created_seq": 3},
        {"id": "C", "severity": "high", "minutes_to_sla": 10, "created_seq": 1},
    ]

    assert prioritize_tickets(tickets) == ["C", "B", "A"]

