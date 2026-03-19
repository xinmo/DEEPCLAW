import type {
  ResearchDepth,
  ResearchHistory,
  GraphNode,
  GraphEdge,
  SSEEvent,
} from '../types/industryResearch';

const API_BASE = '/api/industry-research';

async function expectJson<T>(res: Response, msg: string): Promise<T> {
  if (!res.ok) throw new Error(`${msg}: ${res.status}`);
  return res.json() as Promise<T>;
}

export const industryResearchApi = {
  async startResearch(query: string, depth: ResearchDepth): Promise<{ researchId: string }> {
    const res = await fetch(`${API_BASE}/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, depth }),
    });
    return expectJson(res, '启动研究失败');
  },

  async getHistory(): Promise<ResearchHistory[]> {
    const res = await fetch(`${API_BASE}/history`);
    return expectJson(res, '获取历史失败');
  },

  async getGraph(researchId: string): Promise<{ nodes: GraphNode[]; edges: GraphEdge[] }> {
    const res = await fetch(`${API_BASE}/${researchId}/graph`);
    return expectJson(res, '获取图谱失败');
  },

  async startDeepResearch(researchId: string, nodeId: string, nodeName: string): Promise<{ deepId: string }> {
    const res = await fetch(`${API_BASE}/${researchId}/deep`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nodeId, nodeName }),
    });
    return expectJson(res, '启动深度研究失败');
  },

  /**
   * 订阅研究进度 SSE 流。
   * 调用方负责在组件卸载时调用返回的 EventSource.close() 以避免资源泄漏。
   */
  streamResearch(researchId: string, onEvent: (event: SSEEvent) => void, onError?: (err: Event) => void): EventSource {
    const es = new EventSource(`${API_BASE}/${researchId}/stream`);
    es.onmessage = (e) => {
      try {
        const parsed: SSEEvent = JSON.parse(e.data);
        onEvent(parsed);
      } catch (err) {
        console.warn('[IndustryResearch SSE] Failed to parse event', err, e.data);
      }
    };
    if (onError) es.onerror = onError;
    return es;
  },

  /**
   * 订阅深度研究 SSE 流。
   * 调用方负责在组件卸载时调用返回的 EventSource.close() 以避免资源泄漏。
   */
  streamDeepResearch(deepId: string, onEvent: (event: SSEEvent) => void, onError?: (err: Event) => void): EventSource {
    const es = new EventSource(`${API_BASE}/deep/${deepId}/stream`);
    es.onmessage = (e) => {
      try {
        const parsed: SSEEvent = JSON.parse(e.data);
        onEvent(parsed);
      } catch (err) {
        console.warn('[IndustryResearch SSE] Failed to parse deep event', err, e.data);
      }
    };
    if (onError) es.onerror = onError;
    return es;
  },
};
