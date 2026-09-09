# Kata: dependency_unlock

Implemente `unlock_order(tasks)` para determinar a ordem em que tarefas podem ser desbloqueadas.

Entrada:

- `tasks`: dicionario em que a chave e a tarefa e o valor e a lista de dependencias.

Regras:

- Uma tarefa so pode aparecer depois de todas as suas dependencias.
- Quando houver empate, escolha a tarefa alfabeticamente menor.
- Se existir ciclo, levante `ValueError`.

