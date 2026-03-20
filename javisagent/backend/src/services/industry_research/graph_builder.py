import json
from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class NodeData:
    id: str
    label: str
    layer: str
    status: Literal["done", "in_progress", "pending"] = "pending"
    competition_type: Literal["domestic", "foreign", "balanced"] = "balanced"
    nationalization_rate: float = 0.0
    companies: list[dict] = field(default_factory=list)
    overview: str = ""
    upstream_deps: list[str] = field(default_factory=list)
    latest_news: list[str] = field(default_factory=list)
    sort_order: int = 0

    def to_sse_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "layer": self.layer,
            "status": self.status,
            "competitionType": self.competition_type,
            "nationalizationRate": self.nationalization_rate,
            "companies": self.companies,
            "overview": self.overview,
            "upstreamDeps": self.upstream_deps,
            "latestNews": self.latest_news,
        }


@dataclass
class EdgeData:
    source: str
    target: str

    def to_sse_dict(self) -> dict:
        return {"source": self.source, "target": self.target}


class GraphBuilder:
    """Incrementally builds the industry chain graph and tracks state."""

    def __init__(self) -> None:
        self.nodes: dict[str, NodeData] = {}
        self.edges: list[EdgeData] = []

    def add_node(self, node: NodeData) -> None:
        self.nodes[node.id] = node

    def update_node_status(self, node_id: str, status: Literal["done", "in_progress", "pending"]) -> NodeData | None:
        node = self.nodes.get(node_id)
        if node:
            node.status = status
        return node

    def add_edge(self, source: str, target: str) -> EdgeData:
        edge = EdgeData(source=source, target=target)
        self.edges.append(edge)
        return edge

    def to_dict(self) -> dict:
        return {
            "nodes": [n.to_sse_dict() for n in self.nodes.values()],
            "edges": [e.to_sse_dict() for e in self.edges],
        }


def make_sse(event_type: str, data: Any) -> str:
    """Format a single SSE message."""
    return f"data: {json.dumps({'type': event_type, 'data': data}, ensure_ascii=False)}\n\n"
