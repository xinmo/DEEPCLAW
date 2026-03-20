import React, { useCallback, useEffect, useReducer, useRef } from "react";
import type {
  AgentStatus,
  DeepResearchData,
  GraphEdge,
  GraphNode,
  LogEntry,
  ResearchDepth,
  ResearchHistory,
  ResearchView,
  SSEEvent,
} from "../types/industryResearch";
import { industryResearchApi } from "../services/industryResearchApi";

// ---- State & Reducer ----

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
  | { type: "RESET_GRAPH"; researchId: string }
  | { type: "SET_ERROR"; error: string | null };

function reducer(state: ResearchState, action: ResearchAction): ResearchState {
  switch (action.type) {
    case "SET_VIEW":
      return { ...state, view: action.view };
    case "START_RESEARCH":
      return {
        ...state,
        view: "dashboard",
        researchId: action.researchId,
        query: action.query,
        depth: action.depth,
        agents: [],
        logs: [],
        graphNodes: [],
        graphEdges: [],
        progress: 0,
        error: null,
      };
    case "SSE_EVENT": {
      const { event } = action;
      if (event.type === "agent_status") {
        const d = event.data as unknown as AgentStatus;
        const idx = state.agents.findIndex((a) => a.agentId === d.agentId);
        const agents =
          idx >= 0
            ? state.agents.map((a, i) => (i === idx ? d : a))
            : [...state.agents, d];
        return { ...state, agents };
      }
      if (event.type === "log") {
        return { ...state, logs: [...state.logs, event.data as unknown as LogEntry].slice(-100) };
      }
      if (event.type === "graph_node") {
        const node = event.data as unknown as GraphNode;
        const idx = state.graphNodes.findIndex((n) => n.id === node.id);
        const graphNodes =
          idx >= 0
            ? state.graphNodes.map((n, i) => (i === idx ? node : n))
            : [...state.graphNodes, node];
        return { ...state, graphNodes };
      }
      if (event.type === "graph_edge") {
        return { ...state, graphEdges: [...state.graphEdges, event.data as unknown as GraphEdge] };
      }
      if (event.type === "progress") {
        return { ...state, progress: (event.data as { percent: number }).percent };
      }
      if (event.type === "done") {
        return { ...state, view: "graph" };
      }
      if (event.type === "error") {
        return { ...state, error: (event.data as { message: string }).message };
      }
      return state;
    }
    case "SET_HISTORY":
      return { ...state, history: action.history };
    case "SELECT_NODE":
      return { ...state, selectedNodeId: action.nodeId };
    case "START_DEEP":
      return {
        ...state,
        view: "deep",
        deepId: action.deepId,
        deepReport: "",
        deepData: null,
        deepProgress: 0,
      };
    case "DEEP_SSE_EVENT": {
      const { event } = action;
      if (event.type === "report_chunk") {
        return {
          ...state,
          deepReport: state.deepReport + (event.data as { chunk: string }).chunk,
        };
      }
      if (event.type === "deep_data") {
        return { ...state, deepData: event.data as unknown as DeepResearchData };
      }
      if (event.type === "progress") {
        return { ...state, deepProgress: (event.data as { percent: number }).percent };
      }
      if (event.type === "done") {
        return { ...state, deepProgress: 100 };
      }
      if (event.type === "error") {
        return { ...state, error: (event.data as { message: string }).message };
      }
      return state;
    }
    case "SET_LOADING":
      return { ...state, loading: action.loading };
    case "RESET_GRAPH":
      return {
        ...state,
        researchId: action.researchId,
        graphNodes: [],
        graphEdges: [],
        progress: 100,
        agents: [],
        logs: [],
        error: null,
      };
    case "SET_ERROR":
      return { ...state, error: action.error };
    default:
      return state;
  }
}

const initialState: ResearchState = {
  view: "home",
  researchId: null,
  query: "",
  depth: "standard",
  agents: [],
  logs: [],
  graphNodes: [],
  graphEdges: [],
  progress: 0,
  selectedNodeId: null,
  deepId: null,
  deepReport: "",
  deepData: null,
  deepProgress: 0,
  history: [],
  loading: false,
  error: null,
};

// ---- Component ----

const IndustryResearchPage: React.FC = () => {
  const [state, dispatch] = useReducer(reducer, initialState);
  const esRef = useRef<EventSource | null>(null);
  const deepEsRef = useRef<EventSource | null>(null);

  // Load history on mount
  useEffect(() => {
    industryResearchApi
      .getHistory()
      .then((h) => dispatch({ type: "SET_HISTORY", history: h }))
      .catch(() => {});
  }, []);

  // Cleanup SSE on unmount
  useEffect(
    () => () => {
      esRef.current?.close();
      deepEsRef.current?.close();
    },
    [],
  );

  const handleStartResearch = useCallback(
    async (query: string, depth: ResearchDepth) => {
      dispatch({ type: "SET_LOADING", loading: true });
      dispatch({ type: "SET_ERROR", error: null });
      try {
        esRef.current?.close();
        const { researchId } = await industryResearchApi.startResearch(query, depth);
        dispatch({ type: "START_RESEARCH", researchId, query, depth });
        esRef.current = industryResearchApi.streamResearch(
          researchId,
          (event) => {
            dispatch({ type: "SSE_EVENT", event });
            if (event.type === "done" || event.type === "error") {
              esRef.current?.close();
            }
          },
          () => dispatch({ type: "SET_ERROR", error: "研究连接中断，请重试" }),
        );
      } catch {
        dispatch({ type: "SET_ERROR", error: "研究启动失败，请重试" });
      } finally {
        dispatch({ type: "SET_LOADING", loading: false });
      }
    },
    [],
  );

  const handleDeepResearch = useCallback(
    async (nodeId: string, nodeName: string) => {
      if (!state.researchId) return;
      try {
        const { deepId } = await industryResearchApi.startDeepResearch(
          state.researchId,
          nodeId,
          nodeName,
        );
        dispatch({ type: "START_DEEP", deepId });
        dispatch({ type: "SELECT_NODE", nodeId });
        deepEsRef.current?.close();
        deepEsRef.current = industryResearchApi.streamDeepResearch(
          deepId,
          (event) => {
            dispatch({ type: "DEEP_SSE_EVENT", event });
            if (event.type === "done" || event.type === "error") {
              deepEsRef.current?.close();
            }
          },
          () => dispatch({ type: "SET_ERROR", error: "深度研究连接中断" }),
        );
      } catch {
        dispatch({ type: "SET_ERROR", error: "深度研究启动失败，请重试" });
      }
    },
    [state.researchId],
  );

  const handleReviewHistory = useCallback(
    async (researchId: string) => {
      try {
        const { nodes, edges } = await industryResearchApi.getGraph(researchId);
        // Reconstruct state from saved graph
        dispatch({ type: "RESET_GRAPH", researchId });
        dispatch({ type: "SET_VIEW", view: "graph" });
        nodes.forEach((node) =>
          dispatch({ type: "SSE_EVENT", event: { type: "graph_node", data: node as unknown as Record<string, unknown> } }),
        );
        edges.forEach((edge) =>
          dispatch({ type: "SSE_EVENT", event: { type: "graph_edge", data: edge as unknown as Record<string, unknown> } }),
        );
      } catch {
        dispatch({ type: "SET_ERROR", error: "加载历史图谱失败" });
      }
    },
    [],
  );

  const { view } = state;

  // Expose handlers via data attributes for future sub-components (unused vars suppressed)
  void handleDeepResearch;
  void handleReviewHistory;

  return (
    <div style={{ height: "100%", overflow: "hidden" }}>
      {/* TODO Task 6: ResearchHome */}
      {view === "home" && (
        <div style={{ padding: 32 }}>
          <h2>产业研究室首页（Task 6 实现）</h2>
          <p>query: <input onChange={() => {}} /></p>
          <button onClick={() => handleStartResearch("半导体", "standard")}>测试研究</button>
        </div>
      )}
      {/* TODO Task 7: ResearchDashboard */}
      {view === "dashboard" && (
        <div style={{ padding: 32 }}>
          <h2>研究看板（Task 7 实现）</h2>
          <p>进度: {state.progress}%</p>
          <p>节点数: {state.graphNodes.length}</p>
        </div>
      )}
      {/* TODO Task 8: IndustryGraph */}
      {view === "graph" && (
        <div style={{ padding: 32 }}>
          <h2>产业链图谱（Task 8 实现）</h2>
          <p>节点数: {state.graphNodes.length}</p>
          <button onClick={() => dispatch({ type: "SET_VIEW", view: "home" })}>返回</button>
        </div>
      )}
      {/* TODO Task 9: DeepResearch */}
      {view === "deep" && (
        <div style={{ padding: 32 }}>
          <h2>深度研究（Task 9 实现）</h2>
          <p>报告长度: {state.deepReport.length}</p>
          <button onClick={() => dispatch({ type: "SET_VIEW", view: "graph" })}>返回图谱</button>
        </div>
      )}
    </div>
  );
};

export default IndustryResearchPage;
