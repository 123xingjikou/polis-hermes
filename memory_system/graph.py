"""
Knowledge graph: entity-relation management for memory connections.

Inspired by Zep/Graphiti's temporal knowledge graph and cognee's graph-native
approach. Builds a traversable graph of memory items with typed relationships
to enable associative recall and inference.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .base import MemoryItem
from .store import MemoryStore


class KnowledgeGraph:
    def __init__(self, store: MemoryStore):
        self.store = store

    def connect(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
        weight: float = 1.0,
    ) -> bool:
        source = self.store.get(source_id)
        target = self.store.get(target_id)
        if not source or not target:
            return False
        self.store.add_edge(source_id, target_id, relationship, weight)
        return True

    def relate_by_entities(self, agent_id: str) -> int:
        items = self.store.get_by_agent(agent_id, limit=1000)
        count = 0
        for i, item_a in enumerate(items):
            for item_b in items[i + 1:]:
                shared = set(item_a.entities) & set(item_b.entities)
                if shared:
                    for entity in shared:
                        self.store.add_edge(
                            item_a.memory_id,
                            item_b.memory_id,
                            f"shared_entity:{entity}",
                            weight=len(shared) / max(len(item_a.entities), 1),
                        )
                        count += 1
        return count

    def get_neighbors(
        self,
        memory_id: str,
        max_depth: int = 2,
        limit: int = 20,
    ) -> list[MemoryItem]:
        return self.store.get_related_memories(memory_id, max_depth, limit)

    def get_subgraph(
        self,
        entity: str,
        agent_id: str,
        max_depth: int = 2,
    ) -> dict[str, Any]:
        items = self.store.get_by_agent(agent_id, limit=1000)
        seed_items = [i for i in items if entity in i.entities]
        if not seed_items:
            return {"nodes": [], "edges": [], "entity": entity}

        visited: set[str] = set()
        edges: list[dict[str, Any]] = []
        frontier: set[str] = {s.memory_id for s in seed_items}

        for _ in range(max_depth):
            if not frontier:
                break
            next_frontier: set[str] = set()
            for fid in frontier:
                if fid in visited:
                    continue
                visited.add(fid)
                graph_edges = self.store.get_edges(fid)
                for edge in graph_edges:
                    edges.append(edge)
                    target = edge["target"]
                    if target not in visited:
                        next_frontier.add(target)
            frontier = next_frontier

        nodes = []
        for vid in visited:
            item = self.store.get(vid)
            if item:
                nodes.append({
                    "memory_id": item.memory_id,
                    "content": item.content[:100],
                    "type": item.memory_type.value,
                    "entities": item.entities,
                })

        return {"nodes": nodes, "edges": edges, "entity": entity}

    def extract_entity_network(
        self,
        agent_id: str,
    ) -> dict[str, list[str]]:
        items = self.store.get_by_agent(agent_id, limit=1000)
        network: dict[str, set[str]] = defaultdict(set)
        for item in items:
            for entity in item.entities:
                network[entity].add(item.memory_id)
        return {k: list(v) for k, v in network.items()}

    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 4,
    ) -> list[dict[str, str]] | None:
        if source_id == target_id:
            return []

        visited: set[str] = {source_id}
        queue: list[tuple[str, list[dict[str, str]]]] = [(source_id, [])]

        while queue:
            current, path = queue.pop(0)
            if len(path) >= max_depth:
                continue
            edges = self.store.get_edges(current, direction="out")
            for edge in edges:
                nxt = edge["target"]
                new_path = [*path, {
                        "from": current,
                        "to": nxt,
                        "relationship": edge["relationship"],
                    }]
                if nxt == target_id:
                    return new_path
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append((nxt, new_path))
        return None

    def get_stats(self, agent_id: str) -> dict[str, Any]:
        items = self.store.get_by_agent(agent_id, limit=10000)
        all_edges: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in items:
            if item.memory_id not in seen:
                seen.add(item.memory_id)
                all_edges.extend(self.store.get_edges(item.memory_id))

        relationship_counts: dict[str, int] = {}
        for edge in all_edges:
            rel = edge["relationship"]
            relationship_counts[rel] = relationship_counts.get(rel, 0) + 1

        return {
            "node_count": len(items),
            "edge_count": len(all_edges),
            "relationship_types": relationship_counts,
            "agent_id": agent_id,
        }
