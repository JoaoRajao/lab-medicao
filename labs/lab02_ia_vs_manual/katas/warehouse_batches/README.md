# Kata: warehouse_batches

Implemente `consolidate_batches(batches, today)` para consolidar lotes de estoque.

Entrada:

- `batches`: lista de dicionarios com `sku`, `quantity`, `expires_at` (`YYYY-MM-DD`) e `priority`.
- `today`: data de referencia (`YYYY-MM-DD`).

Regras:

- Ignore lotes vencidos antes de `today`.
- Agrupe por `sku`.
- Some `quantity`.
- Retorne a menor data de validade restante como `next_expiration`.
- Retorne a maior prioridade numerica como `max_priority`.
- Ordene o resultado por `next_expiration` e depois por `sku`.

