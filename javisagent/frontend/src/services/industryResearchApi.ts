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
