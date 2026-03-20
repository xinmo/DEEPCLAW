import React, { useEffect, useRef } from "react";
import type { AgentStatus, GraphEdge, GraphNode, LogEntry } from "../../types/industryResearch";
import AgentLogPanel from "./AgentLogPanel";

const COMPETITION_COLORS: Record<string, string> = {
  domestic: "#52c41a",
  foreign: "#fa8c16",
  balanced: "#1677ff",
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
  agents,
  logs,
  graphNodes,
  graphEdges,
  progress,
  query,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const graphRef = useRef<any>(null);

  // Initialize G6 graph
  useEffect(() => {
    if (!containerRef.current) return;
    let destroyed = false;

    import("@antv/g6").then(({ Graph }) => {
      if (destroyed || !containerRef.current) return;
      if (graphRef.current) {
        graphRef.current.destroy();
      }
      const g = new Graph({
        container: containerRef.current,
        width: containerRef.current.clientWidth || 600,
        height: containerRef.current.clientHeight || 400,
        layout: { type: "dagre", rankdir: "TB", nodesep: 20, ranksep: 40 },
        node: {
          style: {
            fill: "#1677ff",
            stroke: "#1677ff",
            radius: 8,
            labelFill: "#fff",
            labelFontSize: 13,
          },
        },
        edge: { style: { stroke: "#bfbfbf", endArrow: true } },
        behaviors: ["zoom-canvas", "drag-canvas"],
      });
      graphRef.current = g;
    });

    return () => {
      destroyed = true;
      if (graphRef.current) {
        graphRef.current.destroy();
        graphRef.current = null;
      }
    };
  }, []);

  // Update graph data when nodes/edges change
  useEffect(() => {
    if (!graphRef.current || graphNodes.length === 0) return;
    const data = {
      nodes: graphNodes.map((n) => ({
        id: n.id,
        data: { label: `${n.label}\n${n.companies.length}家企业` },
        style: {
          fill: COMPETITION_COLORS[n.competitionType] ?? "#1677ff",
          stroke: COMPETITION_COLORS[n.competitionType] ?? "#1677ff",
          fillOpacity: n.status === "pending" ? 0.3 : 1,
          lineDash: n.status === "pending" ? ([4, 4] as number[]) : [],
          lineWidth: n.status === "in_progress" ? 3 : 1,
        },
      })),
      edges: graphEdges.map((e, i) => ({
        id: `e${i}`,
        source: e.source,
        target: e.target,
      })),
    };
    try {
      graphRef.current.setData(data);
      graphRef.current.render();
    } catch {
      // Graph may not be ready yet
    }
  }, [graphNodes, graphEdges]);

  return (
    <div style={{ display: "flex", height: "100%", overflow: "hidden" }}>
      {/* Left: Agent panel */}
      <div style={{ width: "30%", minWidth: 220, flexShrink: 0, overflowY: "auto" }}>
        <AgentLogPanel agents={agents} logs={logs} progress={progress} query={query} />
      </div>
      {/* Right: G6 graph */}
      <div
        ref={containerRef}
        style={{ flex: 1, background: "#fafafa", position: "relative" }}
      />
    </div>
  );
};

export default ResearchDashboard;
