# Kata: sensor_anomaly

Implemente `detect_anomalies(readings, max_jump, min_value, max_value)` para encontrar anomalias em leituras de sensores.

Regras:

- Uma leitura e anomala se `value` ficar fora do intervalo `[min_value, max_value]`.
- Uma leitura tambem e anomala se a diferenca absoluta para a leitura anterior exceder `max_jump`.
- A primeira leitura so e validada por intervalo.
- Retorne lista de dicionarios com `index`, `value` e `reason`.

