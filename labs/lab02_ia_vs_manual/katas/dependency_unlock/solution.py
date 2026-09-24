from __future__ import annotations


def unlock_order(tasks: dict[str, list[str]]) -> list[str]:
    unlocked: list[str] = []
    done: set[str] = set()
    remaining = set(tasks)

    while remaining:
        ready = sorted(
            task for task in remaining
            if all(dependency in done for dependency in tasks[task])
        )
        if not ready:
            raise ValueError("cycle detected")
        current = ready[0]
        unlocked.append(current)
        done.add(current)
        remaining.remove(current)

    return unlocked
