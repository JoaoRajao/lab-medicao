import pytest

from labs.lab02_ia_vs_manual.katas.dependency_unlock.solution import unlock_order


def test_returns_stable_topological_order() -> None:
    tasks = {
        "deploy": ["test"],
        "test": ["build"],
        "build": ["design"],
        "docs": ["design"],
        "design": [],
    }

    assert unlock_order(tasks) == ["design", "build", "docs", "test", "deploy"]


def test_detects_cycles() -> None:
    tasks = {
        "a": ["b"],
        "b": ["c"],
        "c": ["a"],
    }

    with pytest.raises(ValueError):
        unlock_order(tasks)
