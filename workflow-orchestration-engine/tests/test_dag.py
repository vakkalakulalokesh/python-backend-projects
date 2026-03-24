from __future__ import annotations

import pytest

from app.engine.dag import DAG
from app.schemas.workflow import DagDefinition, EdgeConfig, TaskConfig


def test_valid_dag_creation() -> None:
    d = DagDefinition(
        tasks=[
            TaskConfig(id="a", type="delay", name="A", config={"delay_seconds": 0.01}),
            TaskConfig(id="b", type="delay", name="B", config={"delay_seconds": 0.01}),
        ],
        edges=[EdgeConfig(**{"from": "a", "to": "b"})],
    )
    dag = DAG(d)
    assert {n.task_id for n in dag.get_root_tasks()} == {"a"}
    nxt = dag.get_next_tasks("a", {"a"})
    assert [n.task_id for n in nxt] == ["b"]


def test_cyclic_dag_rejected() -> None:
    d = DagDefinition(
        tasks=[
            TaskConfig(id="a", type="delay", name="A", config={}),
            TaskConfig(id="b", type="delay", name="B", config={}),
        ],
        edges=[
            EdgeConfig(**{"from": "a", "to": "b"}),
            EdgeConfig(**{"from": "b", "to": "a"}),
        ],
    )
    with pytest.raises(ValueError, match="cycle"):
        DAG(d)


def test_parallel_dag() -> None:
    d = DagDefinition(
        tasks=[
            TaskConfig(id="root", type="delay", name="R", config={}),
            TaskConfig(id="l", type="delay", name="L", config={}),
            TaskConfig(id="r", type="delay", name="R2", config={}),
            TaskConfig(id="join", type="delay", name="J", config={}),
        ],
        edges=[
            EdgeConfig(**{"from": "root", "to": "l"}),
            EdgeConfig(**{"from": "root", "to": "r"}),
            EdgeConfig(**{"from": "l", "to": "join"}),
            EdgeConfig(**{"from": "r", "to": "join"}),
        ],
    )
    dag = DAG(d)
    ready_after_root = dag.get_ready_tasks({"root"}, set(), set())
    ids = {n.task_id for n in ready_after_root}
    assert ids == {"l", "r"}


def test_execution_order() -> None:
    d = DagDefinition(
        tasks=[
            TaskConfig(id="a", type="delay", name="A", config={}),
            TaskConfig(id="b", type="delay", name="B", config={}),
            TaskConfig(id="c", type="delay", name="C", config={}),
        ],
        edges=[
            EdgeConfig(**{"from": "a", "to": "b"}),
            EdgeConfig(**{"from": "b", "to": "c"}),
        ],
    )
    dag = DAG(d)
    assert dag.get_execution_order() == [["a"], ["b"], ["c"]]


def test_missing_task_reference() -> None:
    d = DagDefinition(
        tasks=[TaskConfig(id="a", type="delay", name="A", config={})],
        edges=[EdgeConfig(**{"from": "a", "to": "missing"})],
    )
    with pytest.raises(ValueError, match="unknown task"):
        DAG(d)
