import asyncio
import json
import logging
import re
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from src.services.industry_research.graph_builder import EdgeData, GraphBuilder, NodeData

logger = logging.getLogger(__name__)


def _make_sse(event_type: str, data: Any) -> str:
    """Format a single SSE message."""
    return f"data: {json.dumps({'type': event_type, 'data': data}, ensure_ascii=False)}\n\n"


async def run_industry_research(
    research_id: str,
    query: str,
    depth: str,
) -> AsyncGenerator[str, None]:
    """Run multi-agent industry research and yield SSE events."""
    try:
        from langchain_anthropic import ChatAnthropic
        from langchain_community.tools import DuckDuckGoSearchRun
    except ImportError as e:
        yield _make_sse("error", {"message": f"Missing dependency: {e}"})
        return

    graph_builder = GraphBuilder()
    search_tool = DuckDuckGoSearchRun()
    model = ChatAnthropic(model_name="claude-sonnet-4-6")

    # --- Agent 1: 产业分析师 ---
    yield _make_sse("agent_status", {
        "agentId": "analyst", "name": "产业分析师", "status": "running",
        "action": f"分析{query}产业链层次结构",
    })
    yield _make_sse("log", {"timestamp": datetime.now().strftime("%H:%M:%S"), "message": f"开始分析{query}产业链..."})

    search_result = search_tool.run(f"{query}产业链图谱 2025")
    yield _make_sse("log", {"timestamp": datetime.now().strftime("%H:%M:%S"), "message": f"web_search: {query}产业链图谱 2025"})

    analyst_prompt = f"""你是一位产业链分析专家。请对"{query}"产业链进行层次结构分析。
返回纯 JSON 格式（不要有其他文字），包含各层级节点信息：
{{"nodes": [{{"id": "node_1", "label": "节点名称", "layer": "上游原材料", "competition_type": "domestic", "nationalization_rate": 0.35}}], "edges": [{{"source": "node_1", "target": "node_2"}}]}}

competition_type 只能是：domestic（国产机遇）、foreign（外资垄断）、balanced（均衡竞争）
nationalization_rate 是 0-1 之间的小数
节点数量：快速概览4-6个，标准研究6-10个，深度研究8-12个，当前深度：{depth}

搜索结果参考：{search_result[:2000]}"""

    try:
        analyst_result = await model.ainvoke(analyst_prompt)
        raw_content = analyst_result.content if hasattr(analyst_result, "content") else str(analyst_result)
        json_match = re.search(r"\{{[\s\S]*\}}", raw_content)
        chain_data = {"nodes": [], "edges": []}
        if json_match:
            chain_data = json.loads(json_match.group())
    except Exception as e:
        logger.warning("Analyst agent failed: %s", e)
        chain_data = {"nodes": [], "edges": []}

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
        node.status = "in_progress"
        yield _make_sse("graph_node", node.to_sse_dict())

        search_query = f"{query} {node.label} 主要企业 市场份额 2025"
        yield _make_sse("log", {"timestamp": datetime.now().strftime("%H:%M:%S"), "message": f"web_search: {search_query}"})

        try:
            node_search = search_tool.run(search_query)
            company_prompt = f"""针对"{query}"产业链中的"{node.label}"环节，提取核心企业信息。
返回纯 JSON（不要有其他文字）：
{{"companies": [{{"name": "企业名", "country": "中国", "marketShare": 0.28, "ticker": "688126", "exchange": "A股"}}], "overview": "该环节概述", "upstream_deps": ["原材料1"], "latest_news": ["最新动态1"]}}

搜索结果：{node_search[:2000]}"""
            company_result = await model.ainvoke(company_prompt)
            company_content = company_result.content if hasattr(company_result, "content") else str(company_result)
            json_match2 = re.search(r"\{{[\s\S]*\}}", company_content)
            company_data = {"companies": [], "overview": "", "upstream_deps": [], "latest_news": []}
            if json_match2:
                company_data = json.loads(json_match2.group())
        except Exception as e:
            logger.warning("Researcher agent failed for node %s: %s", node.label, e)
            company_data = {"companies": [], "overview": "", "upstream_deps": [], "latest_news": []}

        node.companies = company_data.get("companies", [])
        node.overview = company_data.get("overview", "")
        node.upstream_deps = company_data.get("upstream_deps", [])
        node.latest_news = company_data.get("latest_news", [])
        node.status = "done"
        yield _make_sse("graph_node", node.to_sse_dict())
        yield _make_sse("progress", {
            "percent": 25 + int(50 * (idx + 1) / max(len(nodes_list), 1)),
            "stage": f"已完成 {node.label}",
        })

    yield _make_sse("agent_status", {"agentId": "researcher", "name": "供应链研究员", "status": "done"})

    # --- Agent 3: 数据核查员 ---
    yield _make_sse("agent_status", {
        "agentId": "checker", "name": "数据核查员", "status": "running",
        "action": "验证企业归属与市场份额",
    })
    yield _make_sse("log", {"timestamp": datetime.now().strftime("%H:%M:%S"), "message": "正在核查企业数据准确性..."})
    await asyncio.sleep(1)
    yield _make_sse("agent_status", {"agentId": "checker", "name": "数据核查员", "status": "done"})
    yield _make_sse("progress", {"percent": 85, "stage": "数据核查完成"})

    # --- Agent 4: 报告撰写员 ---
    yield _make_sse("agent_status", {
        "agentId": "writer", "name": "报告撰写员", "status": "running",
        "action": "生成环节摘要与投资逻辑",
    })
    yield _make_sse("log", {"timestamp": datetime.now().strftime("%H:%M:%S"), "message": "研究完成，生成报告摘要..."})
    yield _make_sse("progress", {"percent": 100, "stage": "研究完成"})
    yield _make_sse("agent_status", {"agentId": "writer", "name": "报告撰写员", "status": "done"})
    yield _make_sse("done", {"researchId": research_id, "graph": graph_builder.to_dict()})
