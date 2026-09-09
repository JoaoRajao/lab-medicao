from lab02.katas.invoice_window.solution import calculate_invoice


def test_applies_early_discount() -> None:
    invoice = {
        "amount": 200.0,
        "issued_at": "2026-09-01",
        "due_at": "2026-09-10",
        "early_discount_pct": 5.0,
        "late_fee_pct": 8.0,
    }

    assert calculate_invoice(invoice, "2026-09-08") == {
        "status": "early",
        "final_amount": 190.0,
        "days_delta": -2,
    }


def test_applies_late_fee_once() -> None:
    invoice = {
        "amount": 150.0,
        "issued_at": "2026-09-01",
        "due_at": "2026-09-10",
        "early_discount_pct": 10.0,
        "late_fee_pct": 8.0,
    }

    assert calculate_invoice(invoice, "2026-09-13") == {
        "status": "late",
        "final_amount": 162.0,
        "days_delta": 3,
    }

