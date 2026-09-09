from lab02.katas.sensor_anomaly.solution import detect_anomalies


def test_detects_range_and_jump_anomalies() -> None:
    assert detect_anomalies([10.0, 12.0, 30.0, 31.0, -1.0], 10.0, 0.0, 40.0) == [
        {"index": 2, "value": 30.0, "reason": "jump"},
        {"index": 4, "value": -1.0, "reason": "range"},
    ]


def test_first_reading_is_checked_only_by_range() -> None:
    assert detect_anomalies([120.0, 118.0, 117.0], 5.0, 0.0, 100.0) == [
        {"index": 0, "value": 120.0, "reason": "range"},
    ]

