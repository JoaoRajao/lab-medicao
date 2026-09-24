from __future__ import annotations


def reconcile_routes(planned: list[str], executed: list[str]) -> dict[str, list[str]]:
    planned_index = {stop: index for index, stop in enumerate(planned)}
    planned_set = set(planned)
    executed_set = set(executed)

    visited_in_order = []
    out_of_order = []
    furthest_index = -1
    for stop in executed:
        if stop not in planned_index:
            continue
        current_index = planned_index[stop]
        if current_index < furthest_index:
            out_of_order.append(stop)
        else:
            visited_in_order.append(stop)
            furthest_index = current_index

    missed = [stop for stop in planned if stop not in executed_set]
    extra = [stop for stop in executed if stop not in planned_set]

    return {
        "visited_in_order": visited_in_order,
        "missed": missed,
        "extra": extra,
        "out_of_order": out_of_order,
    }
