import json
import logging
import re
from collections.abc import AsyncGenerator
from typing import Any

logger = logging.getLogger(__name__)


def _make_sse(event_type: str, data: Any) -> str:
    return f"data: {json.dumps({'type': event_type, 'data': data}, ensure_ascii=False)}\n\n"


async def run_deep_research(
    deep_id: str,
    node_name: str,
    query_context: str,
) -> AsyncGenerator[str, None]:
    """Run deep research on a specific industry chain node and yield SSE events."""
    try:
        from langchain_anthropic import ChatAnthropic
        from langchain_community.tools import DuckDuckGoSearchRun
    except ImportError as e:
        yield _make_sse("error", {"message": f"Missing dependency: {e}"})
        return

    model = ChatAnthropic(model_name="claude-sonnet-4-6")
    search_tool = DuckDuckGoSearchRun()

    yield _make_sse("progress", {"percent": 5, "stage": f"开始深度研究 {node_name}"})

    market_search = search_tool.run(f"{node_name} 市场份额 全球竞争格局 2025")
    financial_search = search_tool.run(f"{node_name} A股上市公司 营收 毛利率 2025")
    material_search = search_tool.run(f"{node_name} 上游原材料 价格趋势 2025")

    yield _make_sse("progress", {"percent": 30, "stage": "数据收集完成，提取结构化数据..."})

    data_prompt = f"""对"{node_name}"进行深度研究，基于搜索结果提取结构化数据。
返回纯 JSON（不要其他文字）：
{{"marketShares": [{{"name": "公司", "share": 0.28, "country": "日本"}}],
  "companies": [{{"name": "沪硅产业", "ticker": "688126", "revenue": 42.3, "grossMargin": 18.2, "pe": 68, "domesticContribution": 4}}],
  "materials": [{{"name": "多晶硅", "data": [], "analysis": "价格分析"}}],
  "barriers": [{{"dimension": "技术壁垒", "score": 5}}],
  "risks": [{{"level": "high", "description": "风险描述"}}]
}}

市场数据：{market_search[:1500]}
财务数据：{financial_search[:1500]}
原材料：{material_search[:1000]}"""

    deep_data: dict = {}
    try:
        data_result = await model.ainvoke(data_prompt)
        data_content = data_result.content if hasattr(data_result, "content") else str(data_result)
        json_match = re.search(r"\{{[\s\S]*\}}", data_content)
        if json_match:
            deep_data = json.loads(json_match.group())
    except Exception as e:
        logger.warning("Deep data extraction failed: %s", e)

    yield _make_sse("deep_data", deep_data)
    yield _make_sse("progress", {"percent": 50, "stage": "数据分析完成，生成报告..."})

    report_prompt = f"""请为"{node_name}"撰写一份专业的产业深度研究报告（Markdown 格式），包含：

## 一、行业概述
## 二、全球竞争格局
### 2.1 市场份额分析
## 三、A股投资标的分析
### 3.1 [公司名]（股票代码）
**核心逻辑**：
**财务亮点**：
**风险提示**：
## 四、上游原材料分析
## 五、投资建议

背景：{query_context}
数据参考：{json.dumps(deep_data, ensure_ascii=False)[:2000]}"""

    try:
        async for chunk in model.astream(report_prompt):
            content = chunk.content if hasattr(chunk, "content") else str(chunk)
            if content:
                yield _make_sse("report_chunk", {"chunk": content})
    except Exception as e:
        logger.warning("Report streaming failed: %s", e)
        yield _make_sse("report_chunk", {"chunk": f"\n\n*报告生成遇到问题：{e}*"})

    yield _make_sse("progress", {"percent": 100, "stage": "深度研究完成"})
    yield _make_sse("done", {"deepId": deep_id})
