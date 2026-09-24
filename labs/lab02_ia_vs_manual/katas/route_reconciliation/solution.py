from __future__ import annotations


def reconcile_routes(planned: list[str], executed: list[str]) -> dict[str, list[str]]:
    planned_index = {stop: idx for idx, stop in enumerate(planned)}

    visited_in_order: list[str] = []
    extra: list[str] = []
    out_of_order: list[str] = []
    seen: set[str] = set()
    pointer = 0

    for stop in executed:
        if stop not in planned_index:
            extra.append(stop)
            continue
        seen.add(stop)
        idx = planned_index[stop]
        if idx >= pointer:
            visited_in_order.append(stop)
            pointer = idx + 1
        else:
            out_of_order.append(stop)

    missed = [stop for stop in planned if stop not in seen]

    return {
        "visited_in_order": visited_in_order,
        "missed": missed,
        "extra": extra,
        "out_of_order": out_of_order,
    }