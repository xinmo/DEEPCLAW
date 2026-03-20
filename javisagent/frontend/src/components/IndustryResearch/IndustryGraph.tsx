import React, { useCallback, useEffect, useRef, useState } from "react";
import { Button, Space, Tag, Tooltip, Typography } from "antd";
import {
  ArrowLeftOutlined,
  FullscreenOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
} from "@ant-design/icons";
import type { GraphNode, GraphEdge } from "../../types/industryResearch";
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
  query,
  nodes,
  edges,
  selectedNodeId,
  onNodeSelect,
  onDeepResearch,
  onBack,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const graphRef = useRef<any>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const selectedNode = nodes.find((n) => n.id === selectedNodeId) ?? null;
  const companyCount = nodes.reduce((acc, n) => acc + n.companies.length, 0);

  const handleNodeClick = useCallback(
    (nodeId: string) => {
      onNodeSelect(nodeId);
      setDrawerOpen(true);
    },
    [onNodeSelect],
  );

  useEffect(() => {
    if (!containerRef.current || nodes.length === 0) return;
    let destroyed = false;

    import("@antv/g6").then(({ Graph }) => {
      if (destroyed || !containerRef.current) return;
      if (graphRef.current) {
        graphRef.current.destroy();
      }
      const g = new Graph({
        container: containerRef.current,
        width: containerRef.current.clientWidth || 800,
        height: containerRef.current.clientHeight || 500,
        layout: { type: "dagre", rankdir: "TB", nodesep: 30, ranksep: 60 },
        node: {
          style: {
            radius: 10,
            labelFontSize: 14,
            labelFontWeight: "bold",
            padding: [16, 20] as [number, number],
          },
        },
        edge: { style: { stroke: "#bfbfbf", endArrow: true, lineWidth: 1.5 } },
        behaviors: ["zoom-canvas", "drag-canvas", "drag-element"],
      });
      const data = {
        nodes: nodes.map((n) => ({
          id: n.id,
          data: { label: n.label },
          style: {
            fill: COMPETITION_COLORS[n.competitionType] ?? "#1677ff",
            stroke: COMPETITION_COLORS[n.competitionType] ?? "#1677ff",
            fillOpacity: n.status === "pending" ? 0.3 : 1,
            lineDash: n.status === "pending" ? ([4, 4] as number[]) : [],
            labelFill: n.status === "pending" ? "#666" : "#fff",
          },
        })),
        edges: edges.map((e, i) => ({ id: `e${i}`, source: e.source, target: e.target })),
      };
      g.setData(data);
      g.render();
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      g.on("node:click", (evt: any) => {
        if (evt.itemId) handleNodeClick(String(evt.itemId));
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
  }, [nodes, edges, handleNodeClick]);

  const handleZoomIn = () => graphRef.current?.zoom(1.2);
  const handleZoomOut = () => graphRef.current?.zoom(0.8);
  const handleFullscreen = () => containerRef.current?.requestFullscreen?.();

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", overflow: "hidden" }}>
      {/* Toolbar */}
      <div
        style={{
          padding: "10px 16px",
          background: "#fff",
          borderBottom: "1px solid #f0f0f0",
          display: "flex",
          alignItems: "center",
          gap: 12,
          flexShrink: 0,
        }}
      >
        <Button icon={<ArrowLeftOutlined />} onClick={onBack} size="small">
          返回
        </Button>
        <Text strong>{query} 产业链</Text>
        <Text type="secondary" style={{ fontSize: 12 }}>
          {nodes.length} 层环节 · {companyCount} 家企业
        </Text>
        <div style={{ flex: 1 }} />
        <Space>
          <Tag color="green">🟢 国产机遇</Tag>
          <Tag color="orange">🟠 外资垄断</Tag>
          <Tag color="blue">🔵 均衡竞争</Tag>
        </Space>
        <Button.Group size="small">
          <Tooltip title="放大">
            <Button icon={<ZoomInOutlined />} onClick={handleZoomIn} />
          </Tooltip>
          <Tooltip title="缩小">
            <Button icon={<ZoomOutOutlined />} onClick={handleZoomOut} />
          </Tooltip>
          <Tooltip title="全屏">
            <Button icon={<FullscreenOutlined />} onClick={handleFullscreen} />
          </Tooltip>
        </Button.Group>
        <Button
          type="primary"
          size="small"
          disabled={!selectedNode}
          onClick={() =>
            selectedNode && onDeepResearch(selectedNode.id, selectedNode.label)
          }
        >
          深度研究此图谱
        </Button>
      </div>

      {/* Graph area */}
      <div
        style={{
          flex: 1,
          position: "relative",
          paddingRight: drawerOpen ? 480 : 0,
          transition: "padding-right 0.3s",
          overflow: "hidden",
        }}
      >
        <div ref={containerRef} style={{ width: "100%", height: "100%", background: "#fafafa" }} />
      </div>

      <NodeDrawer
        node={selectedNode}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onDeepResearch={(nodeId, nodeName) => {
          setDrawerOpen(false);
          onDeepResearch(nodeId, nodeName);
        }}
      />
    </div>
  );
};

export default IndustryGraph;
