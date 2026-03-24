from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import networkx as nx

from app.schemas.workflow import DagDefinition


@dataclass
class DAGNode:
    task_id: str
    task_type: str
    task_name: str
    config: dict
    retry_config: Optional[dict] = None
    timeout_seconds: int = 300
    dependencies: list[str] = field(default_factory=list)
    dependents: list[str] = field(default_factory=list)


class DAG:
    def __init__(self, definition: DagDefinition) -> None:
        self.nodes: dict[str, DAGNode] = {}
        self.graph = nx.DiGraph()
        self._parse(definition)
        self._validate()

    def _parse(self, definition: DagDefinition) -> None:
        for t in definition.tasks:
            retry_dict = t.retry.model_dump() if t.retry else None
            timeout = t.timeout_seconds if t.timeout_seconds is not None else 300
            self.nodes[t.id] = DAGNode(
                task_id=t.id,
                task_type=t.type,
                task_name=t.name,
                config=t.config,
                retry_config=retry_dict,
                timeout_seconds=timeout,
            )
            self.graph.add_node(t.id)
        for e in definition.edges:
            if e.from_task not in self.nodes or e.to_task not in self.nodes:
                raise ValueError(f"Edge references unknown task: {e.from_task} -> {e.to_task}")
            self.graph.add_edge(e.from_task, e.to_task)
        for node_id in self.nodes:
            preds = list(self.graph.predecessors(node_id))
            succs = list(self.graph.successors(node_id))
            self.nodes[node_id].dependencies = preds
            self.nodes[node_id].dependents = succs

    def _validate(self) -> None:
        for u, v in self.graph.edges:
            if u not in self.nodes or v not in self.nodes:
                raise ValueError(f"Edge references unknown task: {u} -> {v}")
        if not nx.is_directed_acyclic_graph(self.graph):
            raise ValueError("DAG contains a cycle")
        roots = [n for n in self.graph.nodes if self.graph.in_degree(n) == 0]
        if not roots:
            raise ValueError("DAG must have at least one root task with no dependencies")

    def get_root_tasks(self) -> list[DAGNode]:
        return [self.nodes[n] for n in self.graph.nodes if self.graph.in_degree(n) == 0]

    def get_next_tasks(self, completed_task_id: str, completed_ids: set[str]) -> list[DAGNode]:
        ready: list[DAGNode] = []
        for succ in self.graph.successors(completed_task_id):
            preds = list(self.graph.predecessors(succ))
            if preds and all(p in completed_ids for p in preds):
                ready.append(self.nodes[succ])
        return ready

    def get_ready_tasks(self, completed_ids: set[str], skipped_ids: set[str], running_ids: set[str]) -> list[DAGNode]:
        ready: list[DAGNode] = []
        for nid, node in self.nodes.items():
            if nid in completed_ids or nid in skipped_ids or nid in running_ids:
                continue
            preds = list(self.graph.predecessors(nid))
            if any(p in skipped_ids for p in preds):
                continue
            if preds and not all(p in completed_ids for p in preds):
                continue
            ready.append(node)
        return ready

    def get_execution_order(self) -> list[list[str]]:
        return [list(gen) for gen in nx.topological_generations(self.graph)]

    def get_task(self, task_id: str) -> DAGNode:
        if task_id not in self.nodes:
            raise KeyError(f"Unknown task id: {task_id}")
        return self.nodes[task_id]

    def predecessors(self, task_id: str) -> list[str]:
        return list(self.graph.predecessors(task_id))

    def successors(self, task_id: str) -> list[str]:
        return list(self.graph.successors(task_id))

    def all_task_ids(self) -> set[str]:
        return set(self.nodes.keys())
