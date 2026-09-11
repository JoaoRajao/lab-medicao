from labs.lab02_ia_vs_manual.katas.sensor_anomaly.solution import detect_anomalies


def test_detects_range_and_jump_anomalies() -> None:
    assert detect_anomalies([10.0, 12.0, 30.0, 31.0, -1.0], 10.0, 0.0, 40.0) == [
        {"index": 2, "value": 30.0, "reason": "jump"},
        {"index": 4, "value": -1.0, "reason": "range"},
    ]


def test_first_reading_is_checked_only_by_range() -> None:
    # As tres leituras estao fora de [0, 100], entao as tres sao anomalias de
    # "range" -- a leitura 0 nao tem antecessora, entao so pode ser marcada
    # por range (nunca por "jump"), que e o comportamento que este teste
    # verifica. As leituras 1 e 2 tambem sao range: a diferenca para a leitura
    # anterior (2.0 e 1.0) fica dentro de max_jump=5.0, entao nenhuma delas
    # seria sinalizada por "jump" -- ficam marcadas como "range" mesmo assim,
    # por estarem fora do intervalo.
    assert detect_anomalies([120.0, 118.0, 117.0], 5.0, 0.0, 100.0) == [
        {"index": 0, "value": 120.0, "reason": "range"},
        {"index": 1, "value": 118.0, "reason": "range"},
        {"index": 2, "value": 117.0, "reason": "range"},
    ]

