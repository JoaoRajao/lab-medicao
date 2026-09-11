from labs.lab02_ia_vs_manual.katas.warehouse_batches.solution import consolidate_batches


def test_consolidates_valid_batches_by_sku() -> None:
    batches = [
        {"sku": "A1", "quantity": 5, "expires_at": "2026-09-10", "priority": 1},
        {"sku": "B2", "quantity": 3, "expires_at": "2026-09-12", "priority": 2},
        {"sku": "A1", "quantity": 7, "expires_at": "2026-09-11", "priority": 4},
    ]

    assert consolidate_batches(batches, "2026-09-09") == [
        {"sku": "A1", "quantity": 12, "next_expiration": "2026-09-10", "max_priority": 4},
        {"sku": "B2", "quantity": 3, "next_expiration": "2026-09-12", "max_priority": 2},
    ]


def test_ignores_expired_batches_and_sorts_by_expiration() -> None:
    batches = [
        {"sku": "C3", "quantity": 9, "expires_at": "2026-09-08", "priority": 9},
        {"sku": "B2", "quantity": 1, "expires_at": "2026-09-10", "priority": 1},
        {"sku": "A1", "quantity": 1, "expires_at": "2026-09-10", "priority": 2},
    ]

    assert consolidate_batches(batches, "2026-09-09") == [
        {"sku": "A1", "quantity": 1, "next_expiration": "2026-09-10", "max_priority": 2},
        {"sku": "B2", "quantity": 1, "next_expiration": "2026-09-10", "max_priority": 1},
    ]

