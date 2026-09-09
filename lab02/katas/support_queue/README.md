# Kata: support_queue

Implemente `prioritize_tickets(tickets)` para ordenar tickets de suporte.

Regras:

- Tickets vencidos por SLA (`minutes_to_sla < 0`) tem maior prioridade.
- Depois, ordenar por severidade: `critical`, `high`, `medium`, `low`.
- Depois, menor `minutes_to_sla`.
- Depois, menor `created_seq`.
- Retorne a lista de IDs na ordem de atendimento.

