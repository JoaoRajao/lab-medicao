from __future__ import annotations

import heapq


def unlock_order(tasks: dict[str, list[str]]) -> list[str]:
    indegree = {task: 0 for task in tasks}
    dependents: dict[str, list[str]] = {task: [] for task in tasks}

    for task, deps in tasks.items():
        for dep in deps:
            dependents[dep].append(task)
            indegree[task] += 1

    ready = [task for task, degree in indegree.items() if degree == 0]
    heapq.heapify(ready)

    order: list[str] = []
    while ready:
        task = heapq.heappop(ready)
        order.append(task)
        for dependent in dependents[task]:
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                heapq.heappush(ready, dependent)

    if len(order) != len(tasks):
        raise ValueError("Ciclo detectado entre as tarefas.")

    return order
