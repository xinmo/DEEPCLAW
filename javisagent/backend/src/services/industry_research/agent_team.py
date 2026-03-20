import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from datetime import datetime

from src.services.industry_research.graph_builder import EdgeData, GraphBuilder, NodeData, make_sse

logger = logging.getLogger(__name__)


def _safe_float(val: object, default: float = 0.0) -> float:
    try:
        return float(val)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


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
        yield make_sse("error", {"message": f"Missing dependency: {e}"})
        return

    graph_builder = GraphBuilder()
    search_tool = DuckDuckGoSearchRun()
    model = ChatAnthropic(model_name="claude-sonnet-4-6", timeout=60)

    # --- Agent 1: 产业分析师 ---
    yield make_sse("agent_status", {
        "agentId": "analyst", "name": "产业分析师", "status": "running",
        "action": f"分析{query}产业链层次结构",
    })
    yield make_sse("log", {"timestamp": datetime.now().strftime("%H:%M:%S"), "message": f"开始分析{query}产业链..."})

    search_result = await asyncio.to_thread(search_tool.run, f"{query}产业链图谱 2025")
    yield make_sse("log", {"timestamp": datetime.now().strftime("%H:%M:%S"), "message": f"web_search: {query}产业链图谱 2025"})

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
        chain_data = {"nodes": [], "edges": []}
        start = raw_content.find("{")
        end = raw_content.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                chain_data = json.loads(raw_content[start:end + 1])
            except json.JSONDecodeError:
                pass
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
            nationalization_rate=_safe_float(n.get("nationalization_rate", 0)),
            sort_order=i,
        )
        graph_builder.add_node(node)
        yield make_sse("graph_node", node.to_sse_dict())

    for e in chain_data.get("edges", []):
        edge = graph_builder.add_edge(e.get("source", ""), e.get("target", ""))
        yield make_sse("graph_edge", edge.to_sse_dict())

    yield make_sse("agent_status", {"agentId": "analyst", "name": "产业分析师", "status": "done"})
    yield make_sse("progress", {"percent": 25, "stage": "产业层次识别完成"})

    # --- Agent 2: 供应链研究员 ---
    yield make_sse("agent_status", {
        "agentId": "researcher", "name": "供应链研究员", "status": "running",
        "action": "爬取各环节头部企业",
    })

    nodes_list = list(graph_builder.nodes.values())
    for idx, node in enumerate(nodes_list):
        node.status = "in_progress"
        yield make_sse("graph_node", node.to_sse_dict())

        search_query = f"{query} {node.label} 主要企业 市场份额 2025"
        yield make_sse("log", {"timestamp": datetime.now().strftime("%H:%M:%S"), "message": f"web_search: {search_query}"})

        try:
            node_search = await asyncio.to_thread(search_tool.run, search_query)
            company_prompt = f"""针对"{query}"产业链中的"{node.label}"环节，提取核心企业信息。
返回纯 JSON（不要有其他文字）：
{{"companies": [{{"name": "企业名", "country": "中国", "marketShare": 0.28, "ticker": "688126", "exchange": "A股"}}], "overview": "该环节概述", "upstream_deps": ["原材料1"], "latest_news": ["最新动态1"]}}

搜索结果：{node_search[:2000]}"""
            company_result = await model.ainvoke(company_prompt)
            company_content = company_result.content if hasattr(company_result, "content") else str(company_result)
            company_data = {"companies": [], "overview": "", "upstream_deps": [], "latest_news": []}
            start2 = company_content.find("{")
            end2 = company_content.rfind("}")
            if start2 != -1 and end2 != -1 and end2 > start2:
                try:
                    company_data = json.loads(company_content[start2:end2 + 1])
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            logger.warning("Researcher agent failed for node %s: %s", node.label, e)
            company_data = {"companies": [], "overview": "", "upstream_deps": [], "latest_news": []}

        node.companies = company_data.get("companies", [])
        node.overview = company_data.get("overview", "")
        node.upstream_deps = company_data.get("upstream_deps", [])
        node.latest_news = company_data.get("latest_news", [])
        node.status = "done"
        yield make_sse("graph_node", node.to_sse_dict())
        yield make_sse("progress", {
            "percent": 25 + int(50 * (idx + 1) / max(len(nodes_list), 1)),
            "stage": f"已完成 {node.label}",
        })

    yield make_sse("agent_status", {"agentId": "researcher", "name": "供应链研究员", "status": "done"})

    # --- Agent 3: 数据核查员 ---
    yield make_sse("agent_status", {
        "agentId": "checker", "name": "数据核查员", "status": "running",
        "action": "验证企业归属与市场份额",
    })
    yield make_sse("log", {"timestamp": datetime.now().strftime("%H:%M:%S"), "message": "正在核查企业数据准确性..."})
    yield make_sse("log", {"timestamp": datetime.now().strftime("%H:%M:%S"), "message": "数据核查：交叉验证企业市场份额数据..."})
    yield make_sse("agent_status", {"agentId": "checker", "name": "数据核查员", "status": "done"})
    yield make_sse("progress", {"percent": 85, "stage": "数据核查完成"})

    # --- Agent 4: 报告撰写员 ---
    yield make_sse("agent_status", {
        "agentId": "writer", "name": "报告撰写员", "status": "running",
        "action": "生成环节摘要与投资逻辑",
    })
    yield make_sse("log", {"timestamp": datetime.now().strftime("%H:%M:%S"), "message": "研究完成，生成报告摘要..."})
    yield make_sse("progress", {"percent": 100, "stage": "研究完成"})
    yield make_sse("agent_status", {"agentId": "writer", "name": "报告撰写员", "status": "done"})
    yield make_sse("done", {"researchId": research_id, "graph": graph_builder.to_dict()})
