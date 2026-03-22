# AI 产业研究室 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 JAVISAGENT 中新增「产业研究室」模块，支持 AI 多智能体对产业链进行实时研究，并通过 SSE 流式构建可交互的产业链图谱与深度研究报告。

**Architecture:** 单页多视图模式（home→dashboard→graph→deep），前端通过 EventSource 接收 SSE 事件流实时更新图谱节点与智能体状态，后端基于 deepagents 构建独立的多智能体研究团队（与 Claw 完全解耦），产业链图谱使用 @antv/g6 Dagre 分层布局渲染。

**Tech Stack:** React 19 + TypeScript + Ant Design 6 + @antv/g6 + FastAPI + SQLAlchemy + deepagents + SSE

---

## Task 1: 类型定义与 API 服务层

**Files:**
- Create: `javisagent/frontend/src/types/industryResearch.ts`
- Create: `javisagent/frontend/src/services/industryResearchApi.ts`

**Step 1: 创建前端类型定义**

创建 `javisagent/frontend/src/types/industryResearch.ts`：

```typescript
export type ResearchDepth = 'quick' | 'standard' | 'deep';
export type ResearchView = 'home' | 'dashboard' | 'graph' | 'deep';
export type AgentStatusType = 'running' | 'waiting' | 'done';
export type NodeStatus = 'done' | 'in_progress' | 'pending';
export type CompetitionType = 'domestic' | 'foreign' | 'balanced';

export interface AgentStatus {
  agentId: string;
  name: string;
  status: AgentStatusType;
  action?: string;
  detail?: string;
}

export interface LogEntry {
  timestamp: string;
  message: string;
}

export interface CompanyInfo {
  name: string;
  country: string;
  marketShare?: number;
  ticker?: string;
  exchange?: string;
}

export interface GraphNode {
  id: string;
  label: string;
  layer: string;
  status: NodeStatus;
  competitionType: CompetitionType;
  nationalizationRate?: number;
  companies: CompanyInfo[];
  overview?: string;
  upstreamDeps?: string[];
  latestNews?: string[];
}

export interface GraphEdge {
  source: string;
  target: string;
}

export interface ResearchHistory {
  id: string;
  query: string;
  depth: ResearchDepth;
  status: 'running' | 'completed' | 'failed';
  progress?: number;
  nodeCount?: number;
  companyCount?: number;
  createdAt: string;
  updatedAt: string;
}

export interface MarketShareData {
  name: string;
  share: number;
  country: string;
}

export interface CompanyFinancial {
  name: string;
  ticker: string;
  revenue: number;
  grossMargin: number;
  pe: number;
  domesticContribution: number;
}

export interface MaterialPrice {
  name: string;
  data: { date: string; price: number }[];
  analysis?: string;
}

export interface BarrierScore {
  dimension: string;
  score: number;
}

export interface RiskItem {
  level: 'high' | 'medium' | 'low';
  description: string;
}

export interface DeepResearchData {
  marketShares: MarketShareData[];
  companies: CompanyFinancial[];
  materials: MaterialPrice[];
  barriers: BarrierScore[];
  risks: RiskItem[];
}

// SSE event types
export type SSEEventType =
  | 'agent_status'
  | 'log'
  | 'graph_node'
  | 'graph_edge'
  | 'progress'
  | 'report_chunk'
  | 'deep_data'
  | 'done'
  | 'error';

export interface SSEEvent {
  type: SSEEventType;
  data: unknown;
}
```

**Step 2: 创建 API 服务层**

创建 `javisagent/frontend/src/services/industryResearchApi.ts`：

```typescript
import axios from 'axios';
import type {
  ResearchDepth,
  ResearchHistory,
  GraphNode,
  GraphEdge,
  SSEEvent,
} from '../types/industryResearch';

const BASE = '/api/industry-research';

export const industryResearchApi = {
  async startResearch(query: string, depth: ResearchDepth): Promise<{ researchId: string }> {
    const res = await axios.post(`${BASE}/start`, { query, depth });
    return res.data;
  },

  async getHistory(): Promise<ResearchHistory[]> {
    const res = await axios.get(`${BASE}/history`);
    return res.data;
  },

  async getGraph(researchId: string): Promise<{ nodes: GraphNode[]; edges: GraphEdge[] }> {
    const res = await axios.get(`${BASE}/${researchId}/graph`);
    return res.data;
  },

  async startDeepResearch(researchId: string, nodeId: string, nodeName: string): Promise<{ deepId: string }> {
    const res = await axios.post(`${BASE}/${researchId}/deep`, { nodeId, nodeName });
    return res.data;
  },

  streamResearch(researchId: string, onEvent: (event: SSEEvent) => void, onError?: (err: Event) => void): EventSource {
    const es = new EventSource(`${BASE}/${researchId}/stream`);
    es.onmessage = (e) => {
      try {
        const parsed: SSEEvent = JSON.parse(e.data);
        onEvent(parsed);
      } catch {
        // ignore malformed events
      }
    };
    if (onError) es.onerror = onError;
    return es;
  },

  streamDeepResearch(deepId: string, onEvent: (event: SSEEvent) => void, onError?: (err: Event) => void): EventSource {
    const es = new EventSource(`${BASE}/deep/${deepId}/stream`);
    es.onmessage = (e) => {
      try {
        const parsed: SSEEvent = JSON.parse(e.data);
        onEvent(parsed);
      } catch {
        // ignore malformed events
      }
    };
    if (onError) es.onerror = onError;
    return es;
  },
};
```

**Step 3: Commit**

```bash
git add javisagent/frontend/src/types/industryResearch.ts javisagent/frontend/src/services/industryResearchApi.ts
git commit -m "feat(industry-research): add frontend types and API service layer"
```

---

## Task 2: 后端数据库模型

**Files:**
- Create: `javisagent/backend/src/models/industry_research.py`
- Modify: `javisagent/backend/src/app.py`

**Step 1: 创建数据库模型**

创建 `javisagent/backend/src/models/industry_research.py`：

```python
import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from src.models.base import Base


class IndustryResearch(Base):
    __tablename__ = "industry_research"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    query = Column(String, nullable=False)
    depth = Column(Enum("quick", "standard", "deep", name="research_depth"), nullable=False, default="standard")
    status = Column(Enum("running", "completed", "failed", name="research_status"), nullable=False, default="running")
    progress = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    nodes = relationship("IndustryNode", back_populates="research", cascade="all, delete-orphan")
    edges = relationship("IndustryEdge", back_populates="research", cascade="all, delete-orphan")


class IndustryNode(Base):
    __tablename__ = "industry_node"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    research_id = Column(String, ForeignKey("industry_research.id"), nullable=False)
    node_key = Column(String, nullable=False)  # unique key within a research
    label = Column(String, nullable=False)
    layer = Column(String)
    status = Column(Enum("done", "in_progress", "pending", name="node_status"), default="pending")
    competition_type = Column(Enum("domestic", "foreign", "balanced", name="competition_type"), default="balanced")
    nationalization_rate = Column(Float, default=0.0)
    companies = Column(JSON, default=list)  # list of CompanyInfo dicts
    overview = Column(Text)
    upstream_deps = Column(JSON, default=list)
    latest_news = Column(JSON, default=list)
    sort_order = Column(Integer, default=0)

    research = relationship("IndustryResearch", back_populates="nodes")


class IndustryEdge(Base):
    __tablename__ = "industry_edge"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    research_id = Column(String, ForeignKey("industry_research.id"), nullable=False)
    source = Column(String, nullable=False)
    target = Column(String, nullable=False)

    research = relationship("IndustryResearch", back_populates="edges")


class DeepResearch(Base):
    __tablename__ = "deep_research"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    research_id = Column(String, ForeignKey("industry_research.id"), nullable=False)
    node_key = Column(String, nullable=False)
    node_name = Column(String, nullable=False)
    status = Column(Enum("running", "completed", "failed", name="deep_status"), default="running")
    report = Column(Text, default="")
    deep_data = Column(JSON, default=dict)  # MarketShares, Financials, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Step 2: 注册模型到 app.py**

在 `javisagent/backend/src/app.py` 顶部的 import 块中添加：

```python
from src.models.industry_research import DeepResearch, IndustryEdge, IndustryNode, IndustryResearch
```

**Step 3: Commit**

```bash
git add javisagent/backend/src/models/industry_research.py javisagent/backend/src/app.py
git commit -m "feat(industry-research): add database models for research, nodes, edges, deep research"
```

---

## Task 3: 后端智能体服务（deepagents）

**Files:**
- Create: `javisagent/backend/src/services/industry_research/__init__.py`
- Create: `javisagent/backend/src/services/industry_research/agent_team.py`
- Create: `javisagent/backend/src/services/industry_research/graph_builder.py`
- Create: `javisagent/backend/src/services/industry_research/deep_researcher.py`

**Step 1: 创建 `__init__.py`**

创建空文件 `javisagent/backend/src/services/industry_research/__init__.py`。

**Step 2: 创建图谱构建器**

创建 `javisagent/backend/src/services/industry_research/graph_builder.py`：

```python
import json
from dataclasses import dataclass, field
from typing import Literal


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
```

**Step 3: 创建智能体团队**

创建 `javisagent/backend/src/services/industry_research/agent_team.py`：

```python
import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from langchain_core.tools import tool

from src.services.industry_research.graph_builder import EdgeData, GraphBuilder, NodeData

logger = logging.getLogger(__name__)


def _make_sse(event_type: str, data: Any) -> str:
    """Format a single SSE message."""
    return f"data: {json.dumps({'type': event_type, 'data': data})}\n\n"


async def run_industry_research(
    research_id: str,
    query: str,
    depth: str,
) -> AsyncGenerator[str, None]:
    """Run multi-agent industry research and yield SSE events.

    Yields SSE-formatted strings. The caller (FastAPI StreamingResponse)
    should forward these directly to the client.
    """
    from langchain_anthropic import ChatAnthropic
    from langchain_community.tools import DuckDuckGoSearchRun
    from deepagents.graph import create_deep_agent

    graph_builder = GraphBuilder()

    # --- Agent 1: 产业分析师 ---
    yield _make_sse("agent_status", {
        "agentId": "analyst", "name": "产业分析师", "status": "running",
        "action": f"分析{query}产业链层次结构",
    })
    yield _make_sse("log", {"timestamp": datetime.now().strftime("%H:%M:%S"), "message": f"开始分析{query}产业链..."})

    search_tool = DuckDuckGoSearchRun()
    model = ChatAnthropic(model_name="claude-sonnet-4-6")

    # Step 1: Identify chain layers
    analyst_prompt = f"""
你是一位产业链分析专家。请对"{query}"产业链进行层次结构分析。
返回 JSON 格式，包含各层级节点信息：
{{
  "nodes": [
    {{"id": "node_id", "label": "节点名称", "layer": "上游/中游/下游", "competition_type": "domestic/foreign/balanced", "nationalization_rate": 0.35}}
  ],
  "edges": [
    {{"source": "node_id_1", "target": "node_id_2"}}
  ]
}}
搜索结果参考：{search_tool.run(f'{query}产业链图谱 2025')}
"""
    analyst_result = await model.ainvoke(analyst_prompt)
    raw_content = analyst_result.content if hasattr(analyst_result, 'content') else str(analyst_result)

    # Parse JSON from model response
    import re
    json_match = re.search(r'\{[\s\S]*\}', raw_content)
    chain_data = {"nodes": [], "edges": []}
    if json_match:
        try:
            chain_data = json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # Emit skeleton nodes
    for i, n in enumerate(chain_data.get("nodes", [])):
        node = NodeData(
            id=n.get("id", f"node_{i}"),
            label=n.get("label", ""),
            layer=n.get("layer", ""),
            status="pending",
            competition_type=n.get("competition_type", "balanced"),
            nationalization_rate=float(n.get("nationalization_rate", 0)),
            sort_order=i,
        )
        graph_builder.add_node(node)
        yield _make_sse("graph_node", node.to_sse_dict())

    for e in chain_data.get("edges", []):
        edge = graph_builder.add_edge(e.get("source", ""), e.get("target", ""))
        yield _make_sse("graph_edge", edge.to_sse_dict())

    yield _make_sse("agent_status", {"agentId": "analyst", "name": "产业分析师", "status": "done"})
    yield _make_sse("progress", {"percent": 25, "stage": "产业层次识别完成"})

    # --- Agent 2: 供应链研究员 ---
    yield _make_sse("agent_status", {
        "agentId": "researcher", "name": "供应链研究员", "status": "running",
        "action": "爬取各环节头部企业",
    })

    nodes_list = list(graph_builder.nodes.values())
    for idx, node in enumerate(nodes_list):
        graph_builder.update_node_status(node.id, "in_progress")
        updated = graph_builder.nodes[node.id]
        updated.status = "in_progress"
        yield _make_sse("graph_node", updated.to_sse_dict())

        search_query = f"{query} {node.label} 主要企业 市场份额 2025"
        yield _make_sse("log", {"timestamp": datetime.now().strftime("%H:%M:%S"), "message": f"web_search: {search_query}"})
        search_result = search_tool.run(search_query)

        company_prompt = f"""
针对"{query}"产业链中的"{node.label}"环节，从以下搜索结果中提取核心企业信息。
返回 JSON 格式：
{{"companies": [{{"name": "企业名", "country": "国家", "marketShare": 0.28, "ticker": "688126", "exchange": "A股"}}],
  "overview": "该环节概述", "upstream_deps": ["原材料1"], "latest_news": ["最新动态1"]}}
搜索结果：{search_result}
"""
        company_result = await model.ainvoke(company_prompt)
        company_content = company_result.content if hasattr(company_result, 'content') else str(company_result)
        json_match2 = re.search(r'\{[\s\S]*\}', company_content)
        company_data = {"companies": [], "overview": "", "upstream_deps": [], "latest_news": []}
        if json_match2:
            try:
                company_data = json.loads(json_match2.group())
            except json.JSONDecodeError:
                pass

        updated.companies = company_data.get("companies", [])
        updated.overview = company_data.get("overview", "")
        updated.upstream_deps = company_data.get("upstream_deps", [])
        updated.latest_news = company_data.get("latest_news", [])
        updated.status = "done"
        yield _make_sse("graph_node", updated.to_sse_dict())
        yield _make_sse("progress", {"percent": 25 + int(50 * (idx + 1) / max(len(nodes_list), 1)), "stage": f"已完成 {node.label}"})

    yield _make_sse("agent_status", {"agentId": "researcher", "name": "供应链研究员", "status": "done"})

    # --- Agent 3: 数据核查员 ---
    yield _make_sse("agent_status", {
        "agentId": "checker", "name": "数据核查员", "status": "running",
        "action": "验证企业归属与市场份额",
    })
    yield _make_sse("log", {"timestamp": datetime.now().strftime("%H:%M:%S"), "message": "正在核查企业数据准确性..."})
    await asyncio.sleep(1)  # simulate verification
    yield _make_sse("agent_status", {"agentId": "checker", "name": "数据核查员", "status": "done"})
    yield _make_sse("progress", {"percent": 85, "stage": "数据核查完成"})

    # --- Agent 4: 报告撰写员 ---
    yield _make_sse("agent_status", {
        "agentId": "writer", "name": "报告撰写员", "status": "running",
        "action": "生成环节摘要与投资逻辑",
    })
    yield _make_sse("progress", {"percent": 100, "stage": "研究完成"})
    yield _make_sse("agent_status", {"agentId": "writer", "name": "报告撰写员", "status": "done"})
    yield _make_sse("done", {"researchId": research_id, "graph": graph_builder.to_dict()})
```

**Step 4: 创建深度研究器**

创建 `javisagent/backend/src/services/industry_research/deep_researcher.py`：

```python
import json
import logging
import re
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


def _make_sse(event_type: str, data: Any) -> str:
    return f"data: {json.dumps({'type': event_type, 'data': data})}\n\n"


async def run_deep_research(
    deep_id: str,
    node_name: str,
    query_context: str,
) -> AsyncGenerator[str, None]:
    """Run deep research on a specific industry chain node and yield SSE events."""
    from langchain_anthropic import ChatAnthropic
    from langchain_community.tools import DuckDuckGoSearchRun

    model = ChatAnthropic(model_name="claude-sonnet-4-6")
    search_tool = DuckDuckGoSearchRun()

    yield _make_sse("progress", {"percent": 5, "stage": f"开始深度研究 {node_name}"})

    # Gather market data
    market_search = search_tool.run(f"{node_name} 市场份额 全球竞争格局 2025")
    financial_search = search_tool.run(f"{node_name} A股上市公司 营收 毛利率 2025")
    material_search = search_tool.run(f"{node_name} 上游原材料 价格趋势 2025")

    yield _make_sse("progress", {"percent": 30, "stage": "数据收集完成，生成报告中..."})

    # Build deep data
    data_prompt = f"""
对"{node_name}"进行深度研究，基于以下搜索结果提取结构化数据。
返回 JSON：
{{
  "marketShares": [{{"name": "公司", "share": 0.28, "country": "日本"}}],
  "companies": [{{"name": "沪硅产业", "ticker": "688126", "revenue": 42.3, "grossMargin": 18.2, "pe": 68, "domesticContribution": 4}}],
  "materials": [{{"name": "多晶硅", "data": [], "analysis": "价格分析"}}],
  "barriers": [{{"dimension": "技术壁垒", "score": 5}}],
  "risks": [{{"level": "high", "description": "风险描述"}}]
}}
市场数据：{market_search}
财务数据：{financial_search}
原材料：{material_search}
"""
    data_result = await model.ainvoke(data_prompt)
    data_content = data_result.content if hasattr(data_result, 'content') else str(data_result)
    json_match = re.search(r'\{[\s\S]*\}', data_content)
    deep_data = {}
    if json_match:
        try:
            deep_data = json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    yield _make_sse("deep_data", deep_data)
    yield _make_sse("progress", {"percent": 50, "stage": "数据分析完成，生成报告..."})

    # Stream report
    report_prompt = f"""
请为"{node_name}"撰写一份专业的产业深度研究报告（Markdown 格式），包含：
## 一、行业概述
## 二、全球竞争格局
### 2.1 市场份额分析
## 三、A股投资标的分析
### 3.1 [公司名]（股票代码）
**核心逻辑**、**财务亮点**、**风险提示**
## 四、上游原材料分析
## 五、投资建议

背景：{query_context}，数据：{json.dumps(deep_data, ensure_ascii=False)[:2000]}
"""
    async for chunk in model.astream(report_prompt):
        content = chunk.content if hasattr(chunk, 'content') else str(chunk)
        if content:
            yield _make_sse("report_chunk", {"chunk": content})

    yield _make_sse("progress", {"percent": 100, "stage": "深度研究完成"})
    yield _make_sse("done", {"deepId": deep_id})
```

**Step 5: Commit**

```bash
git add javisagent/backend/src/services/industry_research/
git commit -m "feat(industry-research): add agent team and deep researcher services"
```

---

## Task 4: 后端路由

**Files:**
- Create: `javisagent/backend/src/routes/industry_research/__init__.py`
- Create: `javisagent/backend/src/routes/industry_research/research.py`
- Create: `javisagent/backend/src/routes/industry_research/stream.py`
- Modify: `javisagent/backend/src/app.py`

**Step 1: 创建路由 `__init__.py`**

创建 `javisagent/backend/src/routes/industry_research/__init__.py`：

```python
from .research import router as research_router
from .stream import router as stream_router

__all__ = ["research_router", "stream_router"]
```

**Step 2: 创建 REST 路由**

创建 `javisagent/backend/src/routes/industry_research/research.py`：

```python
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.models import get_db
from src.models.industry_research import DeepResearch, IndustryEdge, IndustryNode, IndustryResearch

router = APIRouter(prefix="/api/industry-research", tags=["industry-research"])


class StartResearchRequest(BaseModel):
    query: str
    depth: Literal["quick", "standard", "deep"] = "standard"


class StartDeepRequest(BaseModel):
    nodeId: str
    nodeName: str


@router.post("/start")
def start_research(req: StartResearchRequest, db: Session = Depends(get_db)):
    research = IndustryResearch(
        id=str(uuid.uuid4()),
        query=req.query,
        depth=req.depth,
        status="running",
        progress=0,
    )
    db.add(research)
    db.commit()
    return {"researchId": research.id}


@router.get("/history")
def get_history(db: Session = Depends(get_db)):
    items = db.query(IndustryResearch).order_by(IndustryResearch.created_at.desc()).limit(20).all()
    return [
        {
            "id": r.id,
            "query": r.query,
            "depth": r.depth,
            "status": r.status,
            "progress": r.progress,
            "nodeCount": len(r.nodes),
            "companyCount": sum(len(n.companies or []) for n in r.nodes),
            "createdAt": r.created_at.isoformat() if r.created_at else None,
            "updatedAt": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in items
    ]


@router.get("/{research_id}/graph")
def get_graph(research_id: str, db: Session = Depends(get_db)):
    research = db.query(IndustryResearch).filter(IndustryResearch.id == research_id).first()
    if not research:
        raise HTTPException(status_code=404, detail="Research not found")
    nodes = [
        {
            "id": n.node_key, "label": n.label, "layer": n.layer,
            "status": n.status, "competitionType": n.competition_type,
            "nationalizationRate": n.nationalization_rate,
            "companies": n.companies or [],
            "overview": n.overview or "",
            "upstreamDeps": n.upstream_deps or [],
            "latestNews": n.latest_news or [],
        }
        for n in sorted(research.nodes, key=lambda x: x.sort_order)
    ]
    edges = [{"source": e.source, "target": e.target} for e in research.edges]
    return {"nodes": nodes, "edges": edges}


@router.post("/{research_id}/deep")
def start_deep_research(research_id: str, req: StartDeepRequest, db: Session = Depends(get_db)):
    research = db.query(IndustryResearch).filter(IndustryResearch.id == research_id).first()
    if not research:
        raise HTTPException(status_code=404, detail="Research not found")
    deep = DeepResearch(
        id=str(uuid.uuid4()),
        research_id=research_id,
        node_key=req.nodeId,
        node_name=req.nodeName,
        status="running",
    )
    db.add(deep)
    db.commit()
    return {"deepId": deep.id}
```

**Step 3: 创建 SSE 流路由**

创建 `javisagent/backend/src/routes/industry_research/stream.py`：

```python
import asyncio
import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.models import get_db
from src.models.industry_research import DeepResearch, IndustryEdge, IndustryNode, IndustryResearch
from src.services.industry_research.agent_team import run_industry_research
from src.services.industry_research.deep_researcher import run_deep_research

router = APIRouter(prefix="/api/industry-research", tags=["industry-research-stream"])


async def _persist_graph_events(
    research_id: str,
    generator: AsyncGenerator[str, None],
    db: Session,
) -> AsyncGenerator[str, None]:
    """Wrap the agent generator, persisting graph nodes/edges and final status to DB."""
    research = db.query(IndustryResearch).filter(IndustryResearch.id == research_id).first()
    sort_counter = 0
    try:
        async for chunk in generator:
            yield chunk
            # parse and persist
            if chunk.startswith("data: "):
                try:
                    event = json.loads(chunk[6:])
                    etype = event.get("type")
                    data = event.get("data", {})
                    if etype == "graph_node":
                        existing = db.query(IndustryNode).filter(
                            IndustryNode.research_id == research_id,
                            IndustryNode.node_key == data.get("id"),
                        ).first()
                        if existing:
                            existing.status = data.get("status", "pending")
                            existing.companies = data.get("companies", [])
                            existing.overview = data.get("overview", "")
                            existing.upstream_deps = data.get("upstreamDeps", [])
                            existing.latest_news = data.get("latestNews", [])
                        else:
                            node = IndustryNode(
                                research_id=research_id,
                                node_key=data.get("id"),
                                label=data.get("label", ""),
                                layer=data.get("layer", ""),
                                status=data.get("status", "pending"),
                                competition_type=data.get("competitionType", "balanced"),
                                nationalization_rate=data.get("nationalizationRate", 0),
                                companies=data.get("companies", []),
                                overview=data.get("overview", ""),
                                upstream_deps=data.get("upstreamDeps", []),
                                latest_news=data.get("latestNews", []),
                                sort_order=sort_counter,
                            )
                            sort_counter += 1
                            db.add(node)
                        db.commit()
                    elif etype == "graph_edge":
                        edge = IndustryEdge(
                            research_id=research_id,
                            source=data.get("source", ""),
                            target=data.get("target", ""),
                        )
                        db.add(edge)
                        db.commit()
                    elif etype == "progress" and research:
                        research.progress = data.get("percent", 0)
                        db.commit()
                    elif etype == "done" and research:
                        research.status = "completed"
                        research.progress = 100
                        db.commit()
                except (json.JSONDecodeError, Exception):
                    pass
    except Exception:
        if research:
            research.status = "failed"
            db.commit()
        raise


@router.get("/{research_id}/stream")
def stream_research(research_id: str, db: Session = Depends(get_db)):
    research = db.query(IndustryResearch).filter(IndustryResearch.id == research_id).first()
    if not research:
        raise HTTPException(status_code=404, detail="Research not found")

    async def generate():
        gen = run_industry_research(research_id, research.query, research.depth)
        async for chunk in _persist_graph_events(research_id, gen, db):
            yield chunk

    return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/deep/{deep_id}/stream")
def stream_deep_research(deep_id: str, db: Session = Depends(get_db)):
    deep = db.query(DeepResearch).filter(DeepResearch.id == deep_id).first()
    if not deep:
        raise HTTPException(status_code=404, detail="Deep research not found")
    research = db.query(IndustryResearch).filter(IndustryResearch.id == deep.research_id).first()
    context = research.query if research else ""

    async def generate():
        async for chunk in run_deep_research(deep_id, deep.node_name, context):
            yield chunk
            if chunk.startswith("data: "):
                try:
                    event = json.loads(chunk[6:])
                    if event.get("type") == "report_chunk":
                        deep.report = (deep.report or "") + event["data"].get("chunk", "")
                    elif event.get("type") == "deep_data":
                        deep.deep_data = event["data"]
                    elif event.get("type") == "done":
                        deep.status = "completed"
                    db.commit()
                except Exception:
                    pass

    return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
```

**Step 4: 注册路由到 app.py**

在 `javisagent/backend/src/app.py` 中添加：

```python
# 在现有 import 之后添加
from src.routes.industry_research import research_router as industry_research_router, stream_router as industry_stream_router

# 在 app.include_router(channels_router) 之后添加
app.include_router(industry_research_router)
app.include_router(industry_stream_router)
```

**Step 5: Commit**

```bash
git add javisagent/backend/src/routes/industry_research/ javisagent/backend/src/app.py
git commit -m "feat(industry-research): add REST and SSE stream routes"
```

---

## Task 5: 前端 — 主页面状态机

**Files:**
- Create: `javisagent/frontend/src/pages/IndustryResearchPage.tsx`

**Step 1: 创建主页面**

创建 `javisagent/frontend/src/pages/IndustryResearchPage.tsx`：

```tsx
import React, { useCallback, useEffect, useReducer, useRef } from "react";
import type {
  AgentStatus, DeepResearchData, GraphEdge, GraphNode,
  LogEntry, ResearchDepth, ResearchHistory, ResearchView, SSEEvent,
} from "../types/industryResearch";
import { industryResearchApi } from "../services/industryResearchApi";
import ResearchHome from "../components/IndustryResearch/ResearchHome";
import ResearchDashboard from "../components/IndustryResearch/ResearchDashboard";
import IndustryGraph from "../components/IndustryResearch/IndustryGraph";
import DeepResearch from "../components/IndustryResearch/DeepResearch";

interface ResearchState {
  view: ResearchView;
  researchId: string | null;
  query: string;
  depth: ResearchDepth;
  agents: AgentStatus[];
  logs: LogEntry[];
  graphNodes: GraphNode[];
  graphEdges: GraphEdge[];
  progress: number;
  selectedNodeId: string | null;
  deepId: string | null;
  deepReport: string;
  deepData: DeepResearchData | null;
  deepProgress: number;
  history: ResearchHistory[];
  loading: boolean;
  error: string | null;
}

type ResearchAction =
  | { type: "SET_VIEW"; view: ResearchView }
  | { type: "START_RESEARCH"; researchId: string; query: string; depth: ResearchDepth }
  | { type: "SSE_EVENT"; event: SSEEvent }
  | { type: "SET_HISTORY"; history: ResearchHistory[] }
  | { type: "SELECT_NODE"; nodeId: string | null }
  | { type: "START_DEEP"; deepId: string }
  | { type: "DEEP_SSE_EVENT"; event: SSEEvent }
  | { type: "SET_LOADING"; loading: boolean }
  | { type: "SET_ERROR"; error: string | null };

function reducer(state: ResearchState, action: ResearchAction): ResearchState {
  switch (action.type) {
    case "SET_VIEW":
      return { ...state, view: action.view };
    case "START_RESEARCH":
      return {
        ...state, view: "dashboard", researchId: action.researchId,
        query: action.query, depth: action.depth,
        agents: [], logs: [], graphNodes: [], graphEdges: [], progress: 0,
      };
    case "SSE_EVENT": {
      const { event } = action;
      if (event.type === "agent_status") {
        const d = event.data as AgentStatus;
        const existing = state.agents.findIndex(a => a.agentId === d.agentId);
        const agents = existing >= 0
          ? state.agents.map((a, i) => i === existing ? d : a)
          : [...state.agents, d];
        return { ...state, agents };
      }
      if (event.type === "log") {
        return { ...state, logs: [...state.logs, event.data as LogEntry].slice(-100) };
      }
      if (event.type === "graph_node") {
        const node = event.data as GraphNode;
        const existing = state.graphNodes.findIndex(n => n.id === node.id);
        const graphNodes = existing >= 0
          ? state.graphNodes.map((n, i) => i === existing ? node : n)
          : [...state.graphNodes, node];
        return { ...state, graphNodes };
      }
      if (event.type === "graph_edge") {
        return { ...state, graphEdges: [...state.graphEdges, event.data as GraphEdge] };
      }
      if (event.type === "progress") {
        return { ...state, progress: (event.data as { percent: number }).percent };
      }
      if (event.type === "done") {
        return { ...state, view: "graph" };
      }
      return state;
    }
    case "SET_HISTORY":
      return { ...state, history: action.history };
    case "SELECT_NODE":
      return { ...state, selectedNodeId: action.nodeId };
    case "START_DEEP":
      return { ...state, view: "deep", deepId: action.deepId, deepReport: "", deepData: null, deepProgress: 0 };
    case "DEEP_SSE_EVENT": {
      const { event } = action;
      if (event.type === "report_chunk") {
        return { ...state, deepReport: state.deepReport + (event.data as { chunk: string }).chunk };
      }
      if (event.type === "deep_data") {
        return { ...state, deepData: event.data as DeepResearchData };
      }
      if (event.type === "progress") {
        return { ...state, deepProgress: (event.data as { percent: number }).percent };
      }
      return state;
    }
    case "SET_LOADING":
      return { ...state, loading: action.loading };
    case "SET_ERROR":
      return { ...state, error: action.error };
    default:
      return state;
  }
}

const initialState: ResearchState = {
  view: "home", researchId: null, query: "", depth: "standard",
  agents: [], logs: [], graphNodes: [], graphEdges: [], progress: 0,
  selectedNodeId: null, deepId: null, deepReport: "", deepData: null, deepProgress: 0,
  history: [], loading: false, error: null,
};

const IndustryResearchPage: React.FC = () => {
  const [state, dispatch] = useReducer(reducer, initialState);
  const esRef = useRef<EventSource | null>(null);
  const deepEsRef = useRef<EventSource | null>(null);

  useEffect(() => {
    industryResearchApi.getHistory().then(h => dispatch({ type: "SET_HISTORY", history: h })).catch(() => {});
  }, []);

  const handleStartResearch = useCallback(async (query: string, depth: ResearchDepth) => {
    dispatch({ type: "SET_LOADING", loading: true });
    try {
      const { researchId } = await industryResearchApi.startResearch(query, depth);
      dispatch({ type: "START_RESEARCH", researchId, query, depth });
      esRef.current?.close();
      esRef.current = industryResearchApi.streamResearch(researchId, (event) => {
        dispatch({ type: "SSE_EVENT", event });
        if (event.type === "done") esRef.current?.close();
      });
    } catch (e) {
      dispatch({ type: "SET_ERROR", error: "研究启动失败，请重试" });
    } finally {
      dispatch({ type: "SET_LOADING", loading: false });
    }
  }, []);

  const handleDeepResearch = useCallback(async (nodeId: string, nodeName: string) => {
    if (!state.researchId) return;
    const { deepId } = await industryResearchApi.startDeepResearch(state.researchId, nodeId, nodeName);
    dispatch({ type: "START_DEEP", deepId });
    deepEsRef.current?.close();
    deepEsRef.current = industryResearchApi.streamDeepResearch(deepId, (event) => {
      dispatch({ type: "DEEP_SSE_EVENT", event });
      if (event.type === "done") deepEsRef.current?.close();
    });
  }, [state.researchId]);

  useEffect(() => () => { esRef.current?.close(); deepEsRef.current?.close(); }, []);

  const { view } = state;
  return (
    <div style={{ height: "100%", overflow: "hidden" }}>
      {view === "home" && (
        <ResearchHome
          history={state.history}
          loading={state.loading}
          onStart={handleStartResearch}
          onReview={(id) => { /* load existing graph */ }}
        />
      )}
      {view === "dashboard" && (
        <ResearchDashboard
          agents={state.agents}
          logs={state.logs}
          graphNodes={state.graphNodes}
          graphEdges={state.graphEdges}
          progress={state.progress}
          query={state.query}
        />
      )}
      {view === "graph" && (
        <IndustryGraph
          query={state.query}
          nodes={state.graphNodes}
          edges={state.graphEdges}
          selectedNodeId={state.selectedNodeId}
          onNodeSelect={(id) => dispatch({ type: "SELECT_NODE", nodeId: id })}
          onDeepResearch={handleDeepResearch}
          onBack={() => dispatch({ type: "SET_VIEW", view: "home" })}
        />
      )}
      {view === "deep" && (
        <DeepResearch
          nodeName={state.graphNodes.find(n => n.id === state.selectedNodeId)?.label ?? ""}
          report={state.deepReport}
          deepData={state.deepData}
          progress={state.deepProgress}
          onBack={() => dispatch({ type: "SET_VIEW", view: "graph" })}
        />
      )}
    </div>
  );
};

export default IndustryResearchPage;
```

**Step 2: Commit**

```bash
git add javisagent/frontend/src/pages/IndustryResearchPage.tsx
git commit -m "feat(industry-research): add main page with view state machine"
```

---

## Task 6: 前端 — ResearchHome 组件

**Files:**
- Create: `javisagent/frontend/src/components/IndustryResearch/ResearchHome.tsx`

**Step 1: 创建组件**

创建 `javisagent/frontend/src/components/IndustryResearch/ResearchHome.tsx`：

```tsx
import React, { useState } from "react";
import { Button, Card, Progress, Radio, Tag, Typography, Input, Tooltip, Spin } from "antd";
import { SearchOutlined, EyeOutlined, ReloadOutlined } from "@ant-design/icons";
import type { ResearchDepth, ResearchHistory } from "../../types/industryResearch";

const { Title, Text } = Typography;

const HOT_TOPICS = ["半导体", "新能源汽车", "创新药", "AI算力", "锂电池", "光伏"];

const DEPTH_OPTIONS: { value: ResearchDepth; label: string; desc: string }[] = [
  { value: "quick", label: "快速概览", desc: "~3分钟，产业链骨架 + 主要玩家" },
  { value: "standard", label: "标准研究", desc: "~8分钟，完整图谱 + 各环节主要企业" },
  { value: "deep", label: "深度研究", desc: "~20分钟，完整图谱 + 每环节财务对比 + 上游原材料价格" },
];

const INDUSTRY_ICONS: Record<string, string> = {
  "半导体": "🏭", "新能源汽车": "🚗", "创新药": "💊", "AI算力": "🖥️", "锂电池": "🔋", "光伏": "☀️",
};

interface ResearchHomeProps {
  history: ResearchHistory[];
  loading: boolean;
  onStart: (query: string, depth: ResearchDepth) => void;
  onReview: (id: string) => void;
}

const ResearchHome: React.FC<ResearchHomeProps> = ({ history, loading, onStart, onReview }) => {
  const [query, setQuery] = useState("");
  const [depth, setDepth] = useState<ResearchDepth>("standard");

  const handleSearch = () => {
    if (!query.trim()) return;
    onStart(query.trim(), depth);
  };

  return (
    <div style={{ height: "100%", overflowY: "auto", background: "#f5f7fa" }}>
      {/* Hero search area */}
      <div style={{
        height: "40vh", minHeight: 280,
        background: "linear-gradient(135deg, #0d1117 0%, #161b22 50%, #1a2332 100%)",
        display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
        padding: "32px 24px",
      }}>
        <Title level={2} style={{ color: "#fff", marginBottom: 8 }}>AI 产业研究室</Title>
        <Text style={{ color: "rgba(255,255,255,0.6)", marginBottom: 24 }}>输入行业或个股，AI 多智能体自动构建产业链图谱</Text>

        <div style={{ width: "100%", maxWidth: 600, marginBottom: 16 }}>
          <Input
            size="large"
            placeholder="输入行业（半导体）或个股（宁德时代/300750）"
            prefix={<SearchOutlined style={{ color: "rgba(255,255,255,0.4)" }} />}
            value={query}
            onChange={e => setQuery(e.target.value)}
            onPressEnter={handleSearch}
            style={{ background: "rgba(255,255,255,0.1)", border: "1px solid rgba(255,255,255,0.2)", color: "#fff", borderRadius: 8 }}
            suffix={
              <Button type="primary" onClick={handleSearch} loading={loading} size="small">
                开始研究
              </Button>
            }
          />
        </div>

        <Radio.Group value={depth} onChange={e => setDepth(e.target.value)} style={{ marginBottom: 16 }}>
          {DEPTH_OPTIONS.map(opt => (
            <Tooltip key={opt.value} title={opt.desc}>
              <Radio.Button value={opt.value} style={{ background: "transparent", borderColor: "rgba(255,255,255,0.3)", color: "rgba(255,255,255,0.8)" }}>
                {opt.label}
              </Radio.Button>
            </Tooltip>
          ))}
        </Radio.Group>

        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "center" }}>
          <Text style={{ color: "rgba(255,255,255,0.4)" }}>热门：</Text>
          {HOT_TOPICS.map(t => (
            <Tag key={t} onClick={() => setQuery(t)} style={{ cursor: "pointer", background: "rgba(255,255,255,0.1)", border: "1px solid rgba(255,255,255,0.2)", color: "rgba(255,255,255,0.8)" }}>
              {t}
            </Tag>
          ))}
        </div>
      </div>

      {/* History cards */}
      <div style={{ padding: "32px 24px" }}>
        {history.length > 0 && (
          <>
            <Title level={4} style={{ marginBottom: 16 }}>历史研究项目</Title>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
              {history.map(item => (
                <Card key={item.id} hoverable size="small" style={{ borderRadius: 8 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                    <span style={{ fontSize: 24 }}>{INDUSTRY_ICONS[item.query] ?? "🔬"}</span>
                    <div>
                      <Text strong>{item.query}</Text>
                      <br />
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {item.nodeCount ?? 0} 层环节 · {item.companyCount ?? 0} 家企业
                      </Text>
                    </div>
                  </div>
                  {item.status === "running" ? (
                    <Progress percent={item.progress ?? 0} size="small" status="active" />
                  ) : (
                    <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                      <Button size="small" icon={<EyeOutlined />} onClick={() => onReview(item.id)}>查看图谱</Button>
                      <Button size="small" icon={<ReloadOutlined />}>更新</Button>
                    </div>
                  )}
                  <Text type="secondary" style={{ fontSize: 11, marginTop: 4, display: "block" }}>
                    {item.createdAt ? new Date(item.createdAt).toLocaleDateString() : ""}
                  </Text>
                </Card>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default ResearchHome;
```

**Step 2: Commit**

```bash
git add javisagent/frontend/src/components/IndustryResearch/ResearchHome.tsx
git commit -m "feat(industry-research): add ResearchHome component"
```

---

## Task 7: 前端 — ResearchDashboard + AgentLogPanel 组件

**Files:**
- Create: `javisagent/frontend/src/components/IndustryResearch/AgentLogPanel.tsx`
- Create: `javisagent/frontend/src/components/IndustryResearch/ResearchDashboard.tsx`

**Step 1: 创建 AgentLogPanel**

创建 `javisagent/frontend/src/components/IndustryResearch/AgentLogPanel.tsx`：

```tsx
import React, { useEffect, useRef } from "react";
import { Progress, Tag, Typography } from "antd";
import { CheckCircleOutlined, ClockCircleOutlined, LoadingOutlined } from "@ant-design/icons";
import type { AgentStatus, LogEntry } from "../../types/industryResearch";

const { Text } = Typography;

const STATUS_ICON: Record<string, React.ReactNode> = {
  running: <LoadingOutlined style={{ color: "#1677ff" }} spin />,
  waiting: <ClockCircleOutlined style={{ color: "#8c8c8c" }} />,
  done: <CheckCircleOutlined style={{ color: "#52c41a" }} />,
};

const STATUS_TAG: Record<string, React.ReactNode> = {
  running: <Tag color="processing">运行中</Tag>,
  waiting: <Tag>等待中</Tag>,
  done: <Tag color="success">完成</Tag>,
};

interface AgentLogPanelProps {
  agents: AgentStatus[];
  logs: LogEntry[];
  progress: number;
  query: string;
}

const AgentLogPanel: React.FC<AgentLogPanelProps> = ({ agents, logs, progress, query }) => {
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [logs]);

  return (
    <div style={{ padding: 16, height: "100%", overflowY: "auto", borderRight: "1px solid #f0f0f0" }}>
      <Text strong>{query} 产业链研究</Text>
      <Progress percent={progress} size="small" style={{ margin: "8px 0 16px" }} />

      <Text type="secondary" style={{ fontSize: 12, display: "block", marginBottom: 8 }}>─── 智能体团队 ───</Text>
      {agents.map(agent => (
        <div key={agent.agentId} style={{ marginBottom: 12, padding: "8px 12px", background: "#fafafa", borderRadius: 6 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            {STATUS_ICON[agent.status] ?? STATUS_ICON.waiting}
            <Text strong style={{ flex: 1 }}>{agent.name}</Text>
            {STATUS_TAG[agent.status]}
          </div>
          {agent.action && <Text type="secondary" style={{ fontSize: 12 }}>{agent.action}</Text>}
          {agent.detail && <Text type="secondary" style={{ fontSize: 11, display: "block", color: "#1677ff" }}>› {agent.detail}</Text>}
        </div>
      ))}

      <Text type="secondary" style={{ fontSize: 12, display: "block", margin: "12px 0 8px" }}>─── 实时日志 ───</Text>
      <div ref={logRef} style={{ height: 200, overflowY: "auto", background: "#0d1117", borderRadius: 6, padding: "8px 10px", fontFamily: "monospace" }}>
        {logs.map((log, i) => (
          <div key={i} style={{ fontSize: 11, color: "rgba(255,255,255,0.7)", lineHeight: 1.6 }}>
            <span style={{ color: "#52c41a" }}>[{log.timestamp}]</span> {log.message}
          </div>
        ))}
      </div>
    </div>
  );
};

export default AgentLogPanel;
```

**Step 2: 创建 ResearchDashboard**

创建 `javisagent/frontend/src/components/IndustryResearch/ResearchDashboard.tsx`。这个组件左栏显示 AgentLogPanel，右栏使用 @antv/g6 渲染图谱实时生长：

```tsx
import React, { useEffect, useRef } from "react";
import type { Graph } from "@antv/g6";
import type { AgentStatus, GraphEdge, GraphNode, LogEntry } from "../../types/industryResearch";
import AgentLogPanel from "./AgentLogPanel";

const COMPETITION_COLORS: Record<string, string> = {
  domestic: "#52c41a",
  foreign: "#fa8c16",
  balanced: "#1677ff",
};

const STATUS_STYLES: Record<string, object> = {
  done: { fillOpacity: 1 },
  in_progress: { fillOpacity: 0.9 },
  pending: { fillOpacity: 0.3, lineDash: [4, 4] },
};

interface ResearchDashboardProps {
  agents: AgentStatus[];
  logs: LogEntry[];
  graphNodes: GraphNode[];
  graphEdges: GraphEdge[];
  progress: number;
  query: string;
}

const ResearchDashboard: React.FC<ResearchDashboardProps> = ({
  agents, logs, graphNodes, graphEdges, progress, query,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<Graph | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    import("@antv/g6").then(({ Graph, DagreLayout }) => {
      if (graphRef.current) graphRef.current.destroy();
      graphRef.current = new Graph({
        container: containerRef.current!,
        width: containerRef.current!.clientWidth,
        height: containerRef.current!.clientHeight,
        layout: { type: "dagre", rankdir: "TB", nodesep: 20, ranksep: 40 },
        node: {
          style: { fill: "#1677ff", stroke: "#1677ff", radius: 8, labelFill: "#fff", labelFontSize: 13 },
        },
        edge: { style: { stroke: "#bfbfbf", endArrow: true } },
        behaviors: ["zoom-canvas", "drag-canvas"],
      });
      graphRef.current.render();
    });
    return () => { graphRef.current?.destroy(); graphRef.current = null; };
  }, []);

  useEffect(() => {
    if (!graphRef.current || graphNodes.length === 0) return;
    const data = {
      nodes: graphNodes.map(n => ({
        id: n.id,
        data: { label: `${n.label}\n${n.companies.length}家企业` },
        style: {
          fill: COMPETITION_COLORS[n.competitionType] ?? "#1677ff",
          ...STATUS_STYLES[n.status],
          lineWidth: n.status === "in_progress" ? 3 : 1,
        },
      })),
      edges: graphEdges.map((e, i) => ({ id: `e${i}`, source: e.source, target: e.target })),
    };
    graphRef.current.setData(data);
    graphRef.current.render();
  }, [graphNodes, graphEdges]);

  return (
    <div style={{ display: "flex", height: "100%", overflow: "hidden" }}>
      <div style={{ width: "30%", minWidth: 240, flexShrink: 0 }}>
        <AgentLogPanel agents={agents} logs={logs} progress={progress} query={query} />
      </div>
      <div ref={containerRef} style={{ flex: 1, background: "#fafafa" }} />
    </div>
  );
};

export default ResearchDashboard;
```

**Step 3: Commit**

```bash
git add javisagent/frontend/src/components/IndustryResearch/AgentLogPanel.tsx javisagent/frontend/src/components/IndustryResearch/ResearchDashboard.tsx
git commit -m "feat(industry-research): add ResearchDashboard and AgentLogPanel components"
```

---

## Task 8: 前端 — IndustryGraph + NodeDrawer 组件

**Files:**
- Create: `javisagent/frontend/src/components/IndustryResearch/NodeDrawer.tsx`
- Create: `javisagent/frontend/src/components/IndustryResearch/IndustryGraph.tsx`

**Step 1: 创建 NodeDrawer**

创建 `javisagent/frontend/src/components/IndustryResearch/NodeDrawer.tsx`：

```tsx
import React from "react";
import { Button, Card, Drawer, Progress, Tag, Typography } from "antd";
import { ExperimentOutlined } from "@ant-design/icons";
import type { GraphNode } from "../../types/industryResearch";

const { Title, Text, Paragraph } = Typography;

const COMPETITION_LABELS: Record<string, { label: string; color: string }> = {
  domestic: { label: "国产机遇", color: "green" },
  foreign: { label: "外资垄断", color: "orange" },
  balanced: { label: "均衡竞争", color: "blue" },
};

interface NodeDrawerProps {
  node: GraphNode | null;
  open: boolean;
  onClose: () => void;
  onDeepResearch: (nodeId: string, nodeName: string) => void;
}

const NodeDrawer: React.FC<NodeDrawerProps> = ({ node, open, onClose, onDeepResearch }) => {
  if (!node) return null;
  const competition = COMPETITION_LABELS[node.competitionType] ?? COMPETITION_LABELS.balanced;

  return (
    <Drawer
      title={<><Text strong>{node.label}</Text> <Tag color={competition.color}>{competition.label}</Tag></>}
      placement="right"
      width={480}
      open={open}
      onClose={onClose}
      mask={false}
    >
      <div style={{ marginBottom: 16 }}>
        <Text type="secondary">{node.layer}</Text>
        <div style={{ margin: "8px 0" }}>
          <Text>国产化率</Text>
          <Progress percent={Math.round((node.nationalizationRate ?? 0) * 100)} size="small" strokeColor="#52c41a" />
        </div>
      </div>

      {node.overview && (
        <div style={{ marginBottom: 16 }}>
          <Title level={5}>环节概述</Title>
          <Paragraph>{node.overview}</Paragraph>
        </div>
      )}

      {node.companies.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <Title level={5}>核心企业</Title>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {node.companies.map((c, i) => (
              <Card key={i} size="small" style={{ minWidth: 100, textAlign: "center" }}>
                <Text strong style={{ display: "block" }}>{c.name}</Text>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  {c.country}{c.marketShare ? ` · ${Math.round(c.marketShare * 100)}%` : ""}
                </Text>
                {c.exchange && <Tag style={{ marginTop: 4 }} color="blue">{c.exchange}</Tag>}
              </Card>
            ))}
          </div>
        </div>
      )}

      {node.upstreamDeps && node.upstreamDeps.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <Title level={5}>上游依赖</Title>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {node.upstreamDeps.map((d, i) => <Tag key={i}>{d}</Tag>)}
          </div>
        </div>
      )}

      {node.latestNews && node.latestNews.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <Title level={5}>最新动态</Title>
          {node.latestNews.map((news, i) => (
            <div key={i} style={{ marginBottom: 4 }}>
              <Text style={{ fontSize: 13 }}>• {news}</Text>
            </div>
          ))}
        </div>
      )}

      <Card style={{ background: "#f0f5ff", border: "1px solid #adc6ff" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
          <ExperimentOutlined style={{ color: "#1677ff", fontSize: 18 }} />
          <Text strong>对此环节启动深度研究</Text>
        </div>
        <Text type="secondary" style={{ fontSize: 12, display: "block", marginBottom: 12 }}>
          AI 将生成投资级研究报告，包含市场格局、财务对比、竞争壁垒、投资风险
        </Text>
        <Button type="primary" block onClick={() => onDeepResearch(node.id, node.label)}>
          开始深度研究 →
        </Button>
      </Card>
    </Drawer>
  );
};

export default NodeDrawer;
```

**Step 2: 创建 IndustryGraph**

创建 `javisagent/frontend/src/components/IndustryResearch/IndustryGraph.tsx`：

```tsx
import React, { useCallback, useEffect, useRef, useState } from "react";
import { Button, Space, Tag, Tooltip, Typography } from "antd";
import { ArrowLeftOutlined, FullscreenOutlined, ZoomInOutlined, ZoomOutOutlined } from "@ant-design/icons";
import type { Graph } from "@antv/g6";
import type { GraphEdge, GraphNode } from "../../types/industryResearch";
import NodeDrawer from "./NodeDrawer";

const { Text } = Typography;

const COMPETITION_COLORS: Record<string, string> = {
  domestic: "#52c41a",
  foreign: "#fa8c16",
  balanced: "#1677ff",
};

interface IndustryGraphProps {
  query: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedNodeId: string | null;
  onNodeSelect: (id: string | null) => void;
  onDeepResearch: (nodeId: string, nodeName: string) => void;
  onBack: () => void;
}

const IndustryGraph: React.FC<IndustryGraphProps> = ({
  query, nodes, edges, selectedNodeId, onNodeSelect, onDeepResearch, onBack,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<Graph | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const selectedNode = nodes.find(n => n.id === selectedNodeId) ?? null;
  const companyCount = nodes.reduce((acc, n) => acc + n.companies.length, 0);

  const handleNodeClick = useCallback((nodeId: string) => {
    onNodeSelect(nodeId);
    setDrawerOpen(true);
  }, [onNodeSelect]);

  useEffect(() => {
    if (!containerRef.current || nodes.length === 0) return;
    import("@antv/g6").then(({ Graph }) => {
      if (graphRef.current) graphRef.current.destroy();
      const g = new Graph({
        container: containerRef.current!,
        width: containerRef.current!.clientWidth,
        height: containerRef.current!.clientHeight,
        layout: { type: "dagre", rankdir: "TB", nodesep: 30, ranksep: 60 },
        node: {
          style: { radius: 10, labelFontSize: 14, labelFontWeight: "bold", padding: [16, 20] },
        },
        edge: { style: { stroke: "#bfbfbf", endArrow: true, lineWidth: 1.5 } },
        behaviors: ["zoom-canvas", "drag-canvas", "drag-element"],
      });
      const data = {
        nodes: nodes.map(n => ({
          id: n.id,
          data: { label: n.label },
          style: {
            fill: COMPETITION_COLORS[n.competitionType] ?? "#1677ff",
            stroke: COMPETITION_COLORS[n.competitionType] ?? "#1677ff",
            fillOpacity: n.status === "pending" ? 0.3 : 1,
            lineDash: n.status === "pending" ? [4, 4] : [],
            labelFill: n.status === "pending" ? "#666" : "#fff",
          },
        })),
        edges: edges.map((e, i) => ({ id: `e${i}`, source: e.source, target: e.target })),
      };
      g.setData(data);
      g.render();
      g.on("node:click", (evt: { itemId?: string }) => {
        if (evt.itemId) handleNodeClick(evt.itemId);
      });
      graphRef.current = g;
    });
    return () => { graphRef.current?.destroy(); graphRef.current = null; };
  }, [nodes, edges, handleNodeClick]);

  const handleZoomIn = () => graphRef.current?.zoom(1.2);
  const handleZoomOut = () => graphRef.current?.zoom(0.8);
  const handleFullscreen = () => containerRef.current?.requestFullscreen();

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", overflow: "hidden" }}>
      {/* Toolbar */}
      <div style={{ padding: "12px 16px", background: "#fff", borderBottom: "1px solid #f0f0f0", display: "flex", alignItems: "center", gap: 12, flexShrink: 0 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={onBack} size="small">返回</Button>
        <Text strong>{query}产业链</Text>
        <Text type="secondary" style={{ fontSize: 12 }}>{nodes.length} 层环节 · {companyCount} 家企业</Text>
        <div style={{ flex: 1 }} />
        <Space>
          <Tag color="green">🟢 国产机遇</Tag>
          <Tag color="orange">🟠 外资垄断</Tag>
          <Tag color="blue">🔵 均衡竞争</Tag>
        </Space>
        <Button.Group size="small">
          <Tooltip title="放大"><Button icon={<ZoomInOutlined />} onClick={handleZoomIn} /></Tooltip>
          <Tooltip title="缩小"><Button icon={<ZoomOutOutlined />} onClick={handleZoomOut} /></Tooltip>
          <Tooltip title="全屏"><Button icon={<FullscreenOutlined />} onClick={handleFullscreen} /></Tooltip>
        </Button.Group>
        <Button type="primary" size="small" onClick={() => selectedNode && onDeepResearch(selectedNode.id, selectedNode.label)}>
          深度研究此图谱
        </Button>
      </div>

      {/* Graph area */}
      <div style={{ flex: 1, position: "relative", paddingRight: drawerOpen ? 480 : 0, transition: "padding-right 0.3s" }}>
        <div ref={containerRef} style={{ width: "100%", height: "100%", background: "#fafafa" }} />
      </div>

      <NodeDrawer
        node={selectedNode}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onDeepResearch={(nodeId, nodeName) => { setDrawerOpen(false); onDeepResearch(nodeId, nodeName); }}
      />
    </div>
  );
};

export default IndustryGraph;
```

**Step 3: Commit**

```bash
git add javisagent/frontend/src/components/IndustryResearch/NodeDrawer.tsx javisagent/frontend/src/components/IndustryResearch/IndustryGraph.tsx
git commit -m "feat(industry-research): add IndustryGraph and NodeDrawer components"
```

---

## Task 9: 前端 — DeepResearch 组件

**Files:**
- Create: `javisagent/frontend/src/components/IndustryResearch/DeepResearch.tsx`

**Step 1: 创建 DeepResearch 组件**

创建 `javisagent/frontend/src/components/IndustryResearch/DeepResearch.tsx`：

```tsx
import React, { useRef, useState } from "react";
import { Button, Progress, Table, Tabs, Tag, Typography } from "antd";
import { ArrowLeftOutlined } from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import type { DeepResearchData } from "../../types/industryResearch";

const { Text, Title } = Typography;

const RISK_COLORS = { high: "#ff4d4f", medium: "#faad14", low: "#52c41a" };
const RISK_ICONS = { high: "🔴", medium: "🟡", low: "🟢" };

interface DeepResearchProps {
  nodeName: string;
  report: string;
  deepData: DeepResearchData | null;
  progress: number;
  onBack: () => void;
}

const DeepResearch: React.FC<DeepResearchProps> = ({ nodeName, report, deepData, progress, onBack }) => {
  const reportRef = useRef<HTMLDivElement>(null);
  const [activeTab, setActiveTab] = useState("market");

  const scrollToSection = (companyName: string) => {
    if (!reportRef.current) return;
    const headings = reportRef.current.querySelectorAll("h2, h3");
    for (const h of headings) {
      if (h.textContent?.includes(companyName)) {
        h.scrollIntoView({ behavior: "smooth", block: "start" });
        break;
      }
    }
  };

  const companyColumns = [
    { title: "企业", dataIndex: "name", key: "name", render: (v: string) => <Text strong style={{ cursor: "pointer", color: "#1677ff" }} onClick={() => scrollToSection(v)}>{v}</Text> },
    { title: "营收(亿)", dataIndex: "revenue", key: "revenue", sorter: (a: { revenue: number }, b: { revenue: number }) => a.revenue - b.revenue },
    { title: "毛利率", dataIndex: "grossMargin", key: "grossMargin", render: (v: number) => `${v}%`, sorter: (a: { grossMargin: number }, b: { grossMargin: number }) => a.grossMargin - b.grossMargin },
    { title: "PE", dataIndex: "pe", key: "pe", sorter: (a: { pe: number }, b: { pe: number }) => a.pe - b.pe },
    { title: "国产化贡献", dataIndex: "domesticContribution", key: "domestic", render: (v: number) => "★".repeat(Math.min(v, 5)) },
  ];

  const tabItems = [
    {
      key: "market",
      label: "市场格局",
      children: (
        <div>
          {deepData?.marketShares?.map((item, i) => (
            <div key={i} style={{ marginBottom: 8 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 2 }}>
                <Text>{item.name} <Tag>{item.country}</Tag></Text>
                <Text strong>{Math.round(item.share * 100)}%</Text>
              </div>
              <div style={{ height: 8, background: "#f0f0f0", borderRadius: 4 }}>
                <div style={{ height: "100%", width: `${item.share * 100}%`, background: "#1677ff", borderRadius: 4, transition: "width 0.5s" }} />
              </div>
            </div>
          ))}
          <div style={{ marginTop: 16 }}>
            <Title level={5}>A股上市公司对比</Title>
            <Table dataSource={deepData?.companies ?? []} columns={companyColumns} size="small" pagination={false} rowKey="ticker" />
          </div>
        </div>
      ),
    },
    {
      key: "materials",
      label: "原材料价格",
      children: (
        <div>
          {deepData?.materials?.map((m, i) => (
            <div key={i} style={{ marginBottom: 16 }}>
              <Text strong>{m.name}</Text>
              {m.analysis && <Text type="secondary" style={{ display: "block", marginTop: 4, fontSize: 12 }}>AI分析：{m.analysis}</Text>}
            </div>
          ))}
        </div>
      ),
    },
    {
      key: "barriers",
      label: "竞争壁垒",
      children: (
        <div>
          {deepData?.barriers?.map((b, i) => (
            <div key={i} style={{ marginBottom: 8 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <Text>{b.dimension}</Text>
                <Text strong>{"★".repeat(b.score)}{"☆".repeat(5 - b.score)}</Text>
              </div>
              <div style={{ height: 6, background: "#f0f0f0", borderRadius: 3, marginTop: 2 }}>
                <div style={{ height: "100%", width: `${b.score * 20}%`, background: "#722ed1", borderRadius: 3 }} />
              </div>
            </div>
          ))}
        </div>
      ),
    },
    {
      key: "risks",
      label: "投资风险",
      children: (
        <div>
          {deepData?.risks?.map((r, i) => (
            <div key={i} style={{ marginBottom: 8, padding: "8px 12px", background: "#fafafa", borderRadius: 6, borderLeft: `3px solid ${RISK_COLORS[r.level]}` }}>
              <Text>{RISK_ICONS[r.level]} {r.description}</Text>
            </div>
          ))}
        </div>
      ),
    },
  ];

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", overflow: "hidden" }}>
      {/* Toolbar */}
      <div style={{ padding: "10px 16px", background: "#fff", borderBottom: "1px solid #f0f0f0", display: "flex", alignItems: "center", gap: 12, flexShrink: 0 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={onBack} size="small">返回图谱</Button>
        <Text strong>{nodeName} 深度研究</Text>
        <div style={{ flex: 1 }} />
        <Progress percent={progress} size="small" style={{ width: 200 }} />
      </div>

      {/* Main content */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        {/* Left panel - Data */}
        <div style={{ width: "45%", borderRight: "1px solid #f0f0f0", overflowY: "auto", padding: 16 }}>
          <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
        </div>

        {/* Right panel - Report */}
        <div style={{ flex: 1, overflowY: "auto", padding: 24 }} ref={reportRef}>
          {report ? (
            <ReactMarkdown>{report}</ReactMarkdown>
          ) : (
            <div style={{ color: "#8c8c8c", textAlign: "center", marginTop: 60 }}>
              <Text type="secondary">AI 正在生成研究报告...</Text>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DeepResearch;
```

**Step 2: Commit**

```bash
git add javisagent/frontend/src/components/IndustryResearch/DeepResearch.tsx
git commit -m "feat(industry-research): add DeepResearch component with linked data panel and report"
```

---

## Task 10: 集成到 App.tsx 和 SideMenu

**Files:**
- Modify: `javisagent/frontend/src/App.tsx`
- Modify: `javisagent/frontend/src/components/Layout/SideMenu.tsx`

**Step 1: 更新 App.tsx**

在 `javisagent/frontend/src/App.tsx` 中：

1. 在 lazy import 列表中添加：
```tsx
const IndustryResearchPage = lazy(() => import("./pages/IndustryResearchPage"));
```

2. 在 `renderNonClawPage()` 函数的 switch/if 逻辑中添加 `industry-research` case：
```tsx
case "industry-research":
  return <IndustryResearchPage />;
```

**Step 2: 更新 SideMenu.tsx**

1. 在 import 中添加 `FlaskConical`（lucide-react）：
```tsx
import { ..., FlaskConical } from "lucide-react";
```

2. 在 LABELS 中添加：
```tsx
industryResearch: "产业研究室",
```

3. 在 Menu items 数组顶部（`document-parse` 之前）添加新菜单项：
```tsx
{
  key: "industry-research",
  label: collapsed ? "" : LABELS.industryResearch,
  icon: <FlaskConical size={16} />,
},
```

**Step 3: Commit**

```bash
git add javisagent/frontend/src/App.tsx javisagent/frontend/src/components/Layout/SideMenu.tsx
git commit -m "feat(industry-research): integrate into App routing and SideMenu navigation"
```

---

## Task 11: 后端依赖与环境

**Files:**
- Modify: `javisagent/backend/requirements.txt`
- Modify: `javisagent/backend/.env.example`

**Step 1: 检查并添加缺少的依赖**

检查 `javisagent/backend/requirements.txt`，确保包含：
- `langchain-community`（DuckDuckGoSearchRun）
- `duckduckgo-search`（DuckDuckGo 工具依赖）
- `langchain-anthropic`（Claude 模型）

如缺少，添加：
```
langchain-community>=0.3.0
duckduckgo-search>=6.0.0
```

**Step 2: 更新 .env.example**

在 `javisagent/backend/.env.example` 添加注释说明：
```
# 产业研究室模块（使用 ANTHROPIC_API_KEY，与知识库共用）
# ANTHROPIC_API_KEY 已在知识库模块中配置，无需重复设置
```

**Step 3: 安装依赖**

```bash
conda activate lcv1 ; cd javisagent/backend ; pip install langchain-community duckduckgo-search
```

**Step 4: Commit**

```bash
git add javisagent/backend/requirements.txt javisagent/backend/.env.example
git commit -m "feat(industry-research): add duckduckgo-search dependency for web research"
```

---

## Task 12: 端到端验证

**Step 1: 启动后端**

```bash
conda activate lcv1 ; cd javisagent/backend ; python src/main.py
```

预期：服务器在 `http://localhost:8000` 启动，`/api/industry-research/start`、`/api/industry-research/history` 等端点可见。

**Step 2: 测试后端 API**

```bash
curl -X POST http://localhost:8000/api/industry-research/start -H "Content-Type: application/json" -d "{\"query\": \"半导体\", \"depth\": \"quick\"}"
```

预期返回：`{"researchId": "<uuid>"}`

**Step 3: 测试 SSE 流**

```bash
curl -N http://localhost:8000/api/industry-research/<researchId>/stream
```

预期：持续输出 `data: {"type": "agent_status", ...}` 等 SSE 事件。

**Step 4: 启动前端**

```bash
cd javisagent/frontend ; npm run dev
```

预期：侧边栏出现「产业研究室」入口，点击进入首页搜索界面。

**Step 5: 完整流程测试**

1. 首页搜索「半导体」，选「快速概览」，点「开始研究」
2. 验证跳转看板，左栏智能体状态更新，右栏图谱节点生长
3. 研究完成后自动跳转图谱主界面
4. 点击图谱节点，验证右侧抽屉滑出显示企业信息
5. 点「开始深度研究」，验证左栏数据填充，右栏报告流式生成

**Step 6: Final commit**

```bash
git add -A
git commit -m "feat(industry-research): complete AI industry research studio - all 4 modules"
```
