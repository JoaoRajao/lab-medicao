# Kata: route_reconciliation

Implemente `reconcile_routes(planned, executed)` para comparar rotas planejadas e executadas.

Entrada:

- `planned`: lista ordenada de paradas planejadas.
- `executed`: lista ordenada de paradas realmente visitadas.

Saida:

- `visited_in_order`: paradas planejadas visitadas na ordem correta.
- `missed`: paradas planejadas nao visitadas.
- `extra`: paradas executadas que nao estavam no plano.
- `out_of_order`: paradas planejadas visitadas, mas fora da ordem esperada.

