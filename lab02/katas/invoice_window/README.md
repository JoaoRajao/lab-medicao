# Kata: invoice_window

Implemente `calculate_invoice(invoice, paid_at)` para calcular cobranca simples.

Entrada:

- `invoice`: dicionario com `amount`, `issued_at`, `due_at`, `early_discount_pct` e `late_fee_pct`.
- `paid_at`: data de pagamento (`YYYY-MM-DD`).

Regras:

- Se pago antes do vencimento, aplique desconto percentual.
- Se pago no vencimento, cobre o valor original.
- Se pago depois do vencimento, aplique multa percentual uma unica vez.
- Arredonde `final_amount` para duas casas decimais.
- Retorne tambem `status`: `early`, `on_time` ou `late`.

