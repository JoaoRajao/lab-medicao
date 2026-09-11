from labs.lab02_ia_vs_manual.katas.route_reconciliation.solution import reconcile_routes


def test_identifies_missed_extra_and_in_order_stops() -> None:
    result = reconcile_routes(
        ["A", "B", "C", "D"],
        ["A", "C", "X", "D"],
    )

    assert result == {
        "visited_in_order": ["A", "C", "D"],
        "missed": ["B"],
        "extra": ["X"],
        "out_of_order": [],
    }


def test_detects_out_of_order_planned_stops() -> None:
    result = reconcile_routes(
        ["A", "B", "C", "D"],
        ["A", "C", "B", "D", "Y"],
    )

    assert result == {
        "visited_in_order": ["A", "C", "D"],
        "missed": [],
        "extra": ["Y"],
        "out_of_order": ["B"],
    }

