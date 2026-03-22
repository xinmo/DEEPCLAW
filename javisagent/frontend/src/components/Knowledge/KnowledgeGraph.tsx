import React, { startTransition, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Alert, Button, Empty, Space, Spin, Tag, Typography, message } from "antd";

import {
  loadGraphRuntime,
  prefetchGraphRuntime,
  readStoredGraphState,
  readStoredGraphViewMode,
  scheduleGraphRuntimePrefetch,
  writeStoredGraphState,
  writeStoredGraphViewMode,
  type GraphViewMode,
} from "../../services/graphRuntime";
import { knowledgeApi } from "../../services/knowledgeApi";
import type { GraphEntity, GraphRelationship, GraphStatistics } from "../../types/knowledge";
import { getEntityTypeColor } from "../../types/knowledge";
import EntityDetailPanel from "./EntityDetailPanel";
import GraphToolbar from "./GraphToolbar";

interface KnowledgeGraphProps {
  kbId: string;
  kbName: string;
  storageKey?: string;
}

interface GraphNeighbor {
  entity: { id: string; name: string; type: string; description?: string };
  relation: { type: string; direction: string; description?: string; weight?: number };
  hop: number;
}

type ExplorerDirection = "all" | "outgoing" | "incoming";

interface KnowledgeNeighborhoodNode {
  entity: GraphEntity;
  depth: number;
}

interface KnowledgeNeighborhoodEdge {
  relationship: GraphRelationship;
  depth: number;
  directionLabel: "Outgoing" | "Incoming";
  counterpartId: string;
  counterpartName: string;
  counterpartType: string;
}

interface KnowledgeExplorerState {
  explorerEntityId: string | null;
  explorerDirection: ExplorerDirection;
  explorerHopDepth: 1 | 2;
  explorerTrail: string[];
  pinnedEntityIds: string[];
}

const DEFAULT_WIDTH = 800;
const DEFAULT_HEIGHT = 520;
const VIEW_MODE_LABELS: Record<GraphViewMode, string> = {
  summary: "Summary",
  explorer: "Explorer",
  interactive: "Interactive",
};
const VIEW_MODE_COPY: Record<GraphViewMode, string> = {
  summary: "Review graph scale and key entities before opening the heavier canvas.",
  explorer: "Browse entities, filter direction, and expand two-hop neighborhoods without booting the graph engine.",
  interactive: "Use the full graph canvas for layout switching, zooming, and free exploration.",
};
const { Paragraph, Text } = Typography;
const KNOWLEDGE_LAYOUT_TYPES = new Set(["force", "circular", "grid", "radial"]);

function getDefaultKnowledgeExplorerState(): KnowledgeExplorerState {
  return {
    explorerEntityId: null,
    explorerDirection: "all",
    explorerHopDepth: 1,
    explorerTrail: [],
    pinnedEntityIds: [],
  };
}

function parseKnowledgeExplorerState(raw: unknown): KnowledgeExplorerState | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }

  const value = raw as Record<string, unknown>;
  return {
    explorerEntityId: typeof value.explorerEntityId === "string" ? value.explorerEntityId : null,
    explorerDirection:
      value.explorerDirection === "incoming" ||
      value.explorerDirection === "outgoing" ||
      value.explorerDirection === "all"
        ? value.explorerDirection
        : "all",
    explorerHopDepth: value.explorerHopDepth === 2 ? 2 : 1,
    explorerTrail: Array.isArray(value.explorerTrail)
      ? value.explorerTrail.filter((item): item is string => typeof item === "string").slice(-8)
      : [],
    pinnedEntityIds: Array.isArray(value.pinnedEntityIds)
      ? value.pinnedEntityIds.filter((item): item is string => typeof item === "string").slice(-6)
      : [],
  };
}

function parseKnowledgeLayout(raw: unknown): string | null {
  return typeof raw === "string" && KNOWLEDGE_LAYOUT_TYPES.has(raw) ? raw : null;
}

function downloadKnowledgeSnapshot(content: string, filename: string, mimeType: string) {
  if (typeof window === "undefined") {
    return;
  }

  const blob = new Blob([content], { type: mimeType });
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.URL.revokeObjectURL(url);
}

function getKnowledgeLayoutConfig(layoutType: string, width: number, height: number) {
  const layoutConfig: Record<string, any> = {
    force: {
      type: "force",
      preventOverlap: true,
      nodeSize: 40,
      linkDistance: 120,
      damping: 0.9,
      maxIteration: 300,
      center: [width / 2, height / 2],
    },
    circular: {
      type: "circular",
      center: [width / 2, height / 2],
    },
    grid: {
      type: "grid",
      center: [width / 2, height / 2],
    },
    radial: {
      type: "radial",
      unitRadius: 80,
      center: [width / 2, height / 2],
    },
  };

  return layoutConfig[layoutType] || layoutConfig.force;
}

function getContainerSize(container: HTMLDivElement | null) {
  return {
    width: Math.max(Math.round(container?.clientWidth || 0), DEFAULT_WIDTH),
    height: Math.max(Math.round(container?.clientHeight || 0), DEFAULT_HEIGHT),
  };
}

function getShortLabel(name: string) {
  return name.length > 10 ? `${name.slice(0, 10)}...` : name;
}

function getClickedNodeId(evt: any): string | undefined {
  return (
    evt?.target?.id ??
    evt?.view?.id ??
    evt?.item?.id ??
    evt?.target?.config?.id ??
    evt?.target?.attributes?.id
  );
}

function buildKnowledgeNeighborhood(
  entities: GraphEntity[],
  relationships: GraphRelationship[],
  rootEntity: GraphEntity | null,
  direction: ExplorerDirection,
  hopDepth: number,
): {
  nodes: KnowledgeNeighborhoodNode[];
  edges: KnowledgeNeighborhoodEdge[];
} {
  if (!rootEntity) {
    return { nodes: [], edges: [] };
  }

  const entityById = new Map(entities.map((entity) => [entity.id, entity]));
  const visitedDepth = new Map<string, number>([[rootEntity.id, 0]]);
  const queue: Array<{ entityId: string; depth: number }> = [{ entityId: rootEntity.id, depth: 0 }];
  const edgeById = new Map<string, KnowledgeNeighborhoodEdge>();

  while (queue.length > 0) {
    const current = queue.shift();
    if (!current) {
      continue;
    }

    if (current.depth >= hopDepth) {
      continue;
    }

    for (const relationship of relationships) {
      const traversals: Array<{ nextId: string; directionLabel: "Outgoing" | "Incoming" }> = [];

      if (
        (direction === "all" || direction === "outgoing") &&
        relationship.source_entity_id === current.entityId
      ) {
        traversals.push({ nextId: relationship.target_entity_id, directionLabel: "Outgoing" });
      }
      if (
        (direction === "all" || direction === "incoming") &&
        relationship.target_entity_id === current.entityId
      ) {
        traversals.push({ nextId: relationship.source_entity_id, directionLabel: "Incoming" });
      }

      for (const traversal of traversals) {
        const nextDepth = current.depth + 1;
        const existingDepth = visitedDepth.get(traversal.nextId);
        if (existingDepth === undefined || nextDepth < existingDepth) {
          visitedDepth.set(traversal.nextId, nextDepth);
          queue.push({ entityId: traversal.nextId, depth: nextDepth });
        }

        const counterpart = entityById.get(traversal.nextId);
        const existingEdge = edgeById.get(relationship.id);
        if (!existingEdge || nextDepth < existingEdge.depth) {
          edgeById.set(relationship.id, {
            relationship,
            depth: nextDepth,
            directionLabel: traversal.directionLabel,
            counterpartId: traversal.nextId,
            counterpartName: counterpart?.name || traversal.nextId,
            counterpartType: counterpart?.type || "--",
          });
        }
      }
    }
  }

  return {
    nodes: Array.from(visitedDepth.entries())
      .map(([entityId, depth]) => {
        const entity = entityById.get(entityId);
        return entity ? { entity, depth } : null;
      })
      .filter((item): item is KnowledgeNeighborhoodNode => Boolean(item))
      .sort((left, right) => {
        if (left.depth !== right.depth) {
          return left.depth - right.depth;
        }
        return left.entity.name.localeCompare(right.entity.name);
      }),
    edges: Array.from(edgeById.values()).sort((left, right) => {
      if (left.depth !== right.depth) {
        return left.depth - right.depth;
      }
      return right.relationship.weight - left.relationship.weight;
    }),
  };
}

const quickCardStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  alignItems: "flex-start",
  gap: 4,
  padding: 12,
  borderRadius: 12,
  border: "1px solid rgba(16, 35, 58, 0.08)",
  background: "#fff",
};

const modeSwitchStyle: React.CSSProperties = {
  display: "flex",
  gap: 8,
  flexWrap: "wrap",
};

const quickGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr",
  gap: 16,
};

const explorerGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1.1fr 0.9fr",
  gap: 16,
};

const KnowledgeGraph: React.FC<KnowledgeGraphProps> = ({
  kbId,
  kbName,
  storageKey: storageKeyProp,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);
  const resizeObserverRef = useRef<ResizeObserver | null>(null);
  const storageKey = storageKeyProp || `knowledge-graph-view-mode:${kbId}`;
  const storedExplorerState = useMemo(
    () =>
      readStoredGraphState(
        storageKey,
        "explorer",
        getDefaultKnowledgeExplorerState(),
        parseKnowledgeExplorerState,
      ),
    [storageKey],
  );

  const [loading, setLoading] = useState(true);
  const [graphReady, setGraphReady] = useState(false);
  const [graphError, setGraphError] = useState<string | null>(null);
  const [statistics, setStatistics] = useState<GraphStatistics | null>(null);
  const [entities, setEntities] = useState<GraphEntity[]>([]);
  const [relationships, setRelationships] = useState<GraphRelationship[]>([]);
  const [selectedEntity, setSelectedEntity] = useState<GraphEntity | null>(null);
  const [selectedEntityNeighbors, setSelectedEntityNeighbors] = useState<GraphNeighbor[]>([]);
  const [detailPanelVisible, setDetailPanelVisible] = useState(false);
  const [filterTypes, setFilterTypes] = useState<string[]>([]);
  const [searchKeyword, setSearchKeyword] = useState("");
  const [viewMode, setViewMode] = useState<GraphViewMode>(() =>
    readStoredGraphViewMode(storageKey, "summary"),
  );
  const [explorerEntityId, setExplorerEntityId] = useState<string | null>(storedExplorerState.explorerEntityId);
  const [explorerDirection, setExplorerDirection] = useState<ExplorerDirection>(
    storedExplorerState.explorerDirection,
  );
  const [explorerHopDepth, setExplorerHopDepth] = useState<1 | 2>(storedExplorerState.explorerHopDepth);
  const [explorerTrail, setExplorerTrail] = useState<string[]>(storedExplorerState.explorerTrail);
  const [pinnedEntityIds, setPinnedEntityIds] = useState<string[]>(storedExplorerState.pinnedEntityIds);
  const [currentLayout, setCurrentLayout] = useState(() =>
    readStoredGraphState(storageKey, "layout", "force", parseKnowledgeLayout),
  );

  const loadGraphData = useCallback(async () => {
    setLoading(true);
    setGraphError(null);

    try {
      const [nextStatistics, nextEntities, nextRelationships] = await Promise.all([
        knowledgeApi.getGraphStatistics(kbId),
        knowledgeApi.getGraphEntities(kbId, undefined, 500),
        knowledgeApi.getGraphRelationships(kbId, 1000),
      ]);
      setStatistics(nextStatistics);
      setEntities(nextEntities);
      setRelationships(nextRelationships);
    } catch (error) {
      console.error("[KnowledgeGraph] failed to load graph data", error);
      setStatistics(null);
      setEntities([]);
      setRelationships([]);
      setGraphError("Graph data failed to load. Check the knowledge extraction result and try again.");
      message.error("Failed to load graph data");
    } finally {
      setLoading(false);
    }
  }, [kbId]);

  useEffect(() => {
    void loadGraphData();
  }, [loadGraphData]);

  useEffect(() => {
    setViewMode(readStoredGraphViewMode(storageKey, "summary"));
  }, [storageKey]);

  useEffect(() => {
    setExplorerEntityId(storedExplorerState.explorerEntityId);
    setExplorerDirection(storedExplorerState.explorerDirection);
    setExplorerHopDepth(storedExplorerState.explorerHopDepth);
    setExplorerTrail(storedExplorerState.explorerTrail);
    setPinnedEntityIds(storedExplorerState.pinnedEntityIds);
    setCurrentLayout(readStoredGraphState(storageKey, "layout", "force", parseKnowledgeLayout));
  }, [storageKey, storedExplorerState]);

  useEffect(() => {
    writeStoredGraphViewMode(storageKey, viewMode);
  }, [storageKey, viewMode]);

  useEffect(() => {
    writeStoredGraphState(storageKey, "explorer", {
      explorerEntityId,
      explorerDirection,
      explorerHopDepth,
      explorerTrail: explorerTrail.slice(-8),
      pinnedEntityIds: pinnedEntityIds.slice(-6),
    });
  }, [
    explorerDirection,
    explorerEntityId,
    explorerHopDepth,
    explorerTrail,
    pinnedEntityIds,
    storageKey,
  ]);

  useEffect(() => {
    writeStoredGraphState(storageKey, "layout", currentLayout);
  }, [currentLayout, storageKey]);

  useEffect(() => {
    if (viewMode === "interactive") {
      scheduleGraphRuntimePrefetch();
    }
  }, [viewMode]);

  const filteredEntities = useMemo(() => {
    let nextEntities = entities;

    if (filterTypes.length > 0) {
      nextEntities = nextEntities.filter((entity) => filterTypes.includes(entity.type));
    }

    if (searchKeyword.trim()) {
      const keyword = searchKeyword.trim().toLowerCase();
      nextEntities = nextEntities.filter((entity) => entity.name.toLowerCase().includes(keyword));
    }

    return [...nextEntities].sort((left, right) => left.name.localeCompare(right.name));
  }, [entities, filterTypes, searchKeyword]);

  const graphData = useMemo(() => {
    const entityIds = new Set(filteredEntities.map((entity) => entity.id));

    return {
      nodes: filteredEntities.map((entity) => {
        const color = getEntityTypeColor(entity.type);
        return {
          id: entity.id,
          data: {
            entityId: entity.id,
            label: getShortLabel(entity.name),
            fullLabel: entity.name,
            description: entity.description,
            type: entity.type,
          },
          style: {
            size: 36,
            fill: color,
            stroke: color,
            lineWidth: 2,
            labelText: getShortLabel(entity.name),
            labelPlacement: "bottom",
            labelFontSize: 11,
          },
        };
      }),
      edges: relationships
        .filter(
          (relationship) =>
            entityIds.has(relationship.source_entity_id) && entityIds.has(relationship.target_entity_id),
        )
        .map((relationship) => ({
          id: relationship.id,
          source: relationship.source_entity_id,
          target: relationship.target_entity_id,
          data: {
            relationType: relationship.relation_type,
            description: relationship.description,
          },
          style: {
            stroke: "#C0C4CC",
            lineWidth: 1,
            endArrow: true,
            labelText: relationship.relation_type,
            labelFontSize: 10,
            labelFill: "#666",
          },
        })),
    };
  }, [filteredEntities, relationships]);

  const openEntityDetail = useCallback(
    async (entity: GraphEntity) => {
      setSelectedEntity(entity);
      setDetailPanelVisible(true);
      try {
        const detail = await knowledgeApi.getGraphEntityDetail(kbId, entity.id, 1);
        setSelectedEntityNeighbors(detail.neighbors);
      } catch (error) {
        console.error("[KnowledgeGraph] failed to load entity detail", error);
        setSelectedEntityNeighbors([]);
      }
    },
    [kbId],
  );

  const topEntities = useMemo(() => filteredEntities.slice(0, 10), [filteredEntities]);
  const topRelationships = useMemo(() => relationships.slice(0, 10), [relationships]);
  const entityTypes = statistics?.entity_types ? Object.keys(statistics.entity_types) : [];

  const focusedExplorerEntity =
    filteredEntities.find((entity) => entity.id === explorerEntityId) ||
    filteredEntities[0] ||
    null;

  const neighborhood = useMemo(
    () => buildKnowledgeNeighborhood(filteredEntities, relationships, focusedExplorerEntity, explorerDirection, explorerHopDepth),
    [explorerDirection, explorerHopDepth, filteredEntities, focusedExplorerEntity, relationships],
  );

  const reachableEntities = neighborhood.nodes.filter((item) => item.depth > 0);
  const isFocusedEntityPinned = focusedExplorerEntity
    ? pinnedEntityIds.includes(focusedExplorerEntity.id)
    : false;
  const comparisonEntity =
    pinnedEntityIds
      .map((entityId) => entities.find((entity) => entity.id === entityId) || null)
      .find((entity) => entity && entity.id !== focusedExplorerEntity?.id) || null;
  const comparisonNeighborhood = useMemo(
    () =>
      buildKnowledgeNeighborhood(
        filteredEntities,
        relationships,
        comparisonEntity,
        explorerDirection,
        explorerHopDepth,
      ),
    [comparisonEntity, explorerDirection, explorerHopDepth, filteredEntities, relationships],
  );
  const comparisonStats = useMemo(() => {
    if (!focusedExplorerEntity || !comparisonEntity) {
      return null;
    }

    const focusEntitySet = new Set(reachableEntities.map((item) => item.entity.id));
    const compareEntitySet = new Set(
      comparisonNeighborhood.nodes.filter((item) => item.depth > 0).map((item) => item.entity.id),
    );
    const focusEdgeSet = new Set(neighborhood.edges.map((item) => item.relationship.id));
    const compareEdgeSet = new Set(comparisonNeighborhood.edges.map((item) => item.relationship.id));
    const sharedEntities = Array.from(focusEntitySet).filter((entityId) => compareEntitySet.has(entityId)).length;
    const sharedEdges = Array.from(focusEdgeSet).filter((edgeId) => compareEdgeSet.has(edgeId)).length;

    return {
      comparisonEntity,
      sharedEntities,
      focusOnlyEntities: Math.max(focusEntitySet.size - sharedEntities, 0),
      compareOnlyEntities: Math.max(compareEntitySet.size - sharedEntities, 0),
      sharedEdges,
    };
  }, [comparisonEntity, comparisonNeighborhood.edges, comparisonNeighborhood.nodes, focusedExplorerEntity, neighborhood.edges, reachableEntities]);
  const trailEntities = explorerTrail
    .map((entityId) => entities.find((entity) => entity.id === entityId) || null)
    .filter((entity): entity is GraphEntity => Boolean(entity));
  const pinnedEntities = pinnedEntityIds
    .map((entityId) => entities.find((entity) => entity.id === entityId) || null)
    .filter((entity): entity is GraphEntity => Boolean(entity));

  useEffect(() => {
    if (!focusedExplorerEntity) {
      setExplorerEntityId(null);
      return;
    }
    if (!explorerEntityId || !filteredEntities.some((entity) => entity.id === explorerEntityId)) {
      setExplorerEntityId(focusedExplorerEntity.id);
    }
  }, [explorerEntityId, filteredEntities, focusedExplorerEntity]);

  useEffect(() => {
    const validEntityIds = new Set(entities.map((entity) => entity.id));
    setPinnedEntityIds((current) => current.filter((entityId) => validEntityIds.has(entityId)));
    setExplorerTrail((current) => current.filter((entityId) => validEntityIds.has(entityId)).slice(-8));
  }, [entities]);

  useEffect(() => {
    if (!focusedExplorerEntity) {
      return;
    }
    setExplorerTrail((current) => {
      if (current[current.length - 1] === focusedExplorerEntity.id) {
        return current;
      }
      const next = [...current.filter((entityId) => entityId !== focusedExplorerEntity.id), focusedExplorerEntity.id];
      return next.slice(-8);
    });
  }, [focusedExplorerEntity]);

  useEffect(() => {
    if (viewMode !== "interactive") {
      resizeObserverRef.current?.disconnect();
      resizeObserverRef.current = null;
      graphRef.current?.destroy?.();
      graphRef.current = null;
      setGraphReady(false);
      return;
    }

    const container = containerRef.current;
    resizeObserverRef.current?.disconnect();
    resizeObserverRef.current = null;
    graphRef.current?.destroy?.();
    graphRef.current = null;
    setGraphReady(false);

    if (!container || loading || graphData.nodes.length === 0) {
      return;
    }

    let disposed = false;

    void (async () => {
      try {
        const { Graph } = await loadGraphRuntime();
        if (disposed) {
          return;
        }

        const { width, height } = getContainerSize(container);
        const graph = new Graph({
          container,
          width,
          height,
          data: graphData as any,
          autoFit: "view",
          padding: [24, 24, 24, 24],
          layout: getKnowledgeLayoutConfig(currentLayout, width, height) as any,
          node: { type: "circle" },
          edge: { type: "line" },
          behaviors: ["drag-canvas", "zoom-canvas", "drag-node", "click-select"],
        });

        graph.on("node:click", async (evt: any) => {
          const nodeId = getClickedNodeId(evt);
          if (!nodeId) {
            return;
          }

          const entity = entities.find((item) => item.id === nodeId);
          if (!entity) {
            return;
          }

          await openEntityDetail(entity);
        });

        await graph.render();
        if (disposed) {
          graph.destroy();
          return;
        }

        graphRef.current = graph;
        setGraphReady(true);
        setGraphError(null);

        requestAnimationFrame(() => {
          if (!disposed) {
            graph.fitView();
          }
        });

        const observer = new ResizeObserver((entries) => {
          if (!graphRef.current || disposed) {
            return;
          }

          const rect = entries[0]?.contentRect;
          const nextWidth = Math.max(Math.round(rect?.width || container.clientWidth || 0), DEFAULT_WIDTH);
          const nextHeight = Math.max(Math.round(rect?.height || container.clientHeight || 0), DEFAULT_HEIGHT);

          graphRef.current.resize(nextWidth, nextHeight);
          graphRef.current.fitView();
        });

        observer.observe(container);
        resizeObserverRef.current = observer;
      } catch (error) {
        console.error("[KnowledgeGraph] render failed", error);
        if (!disposed) {
          setGraphReady(false);
          setGraphError("Graph rendering failed. Refresh the graph and try again.");
          message.error("Failed to render graph");
        }
      }
    })();

    return () => {
      disposed = true;
      resizeObserverRef.current?.disconnect();
      resizeObserverRef.current = null;
      graphRef.current?.destroy?.();
      graphRef.current = null;
    };
  }, [currentLayout, entities, graphData, loading, openEntityDetail, viewMode]);

  useEffect(() => {
    return () => {
      resizeObserverRef.current?.disconnect();
      resizeObserverRef.current = null;
      graphRef.current?.destroy?.();
      graphRef.current = null;
    };
  }, []);

  const handleLayoutChange = async (layoutType: string) => {
    setCurrentLayout(layoutType);
    if (!graphRef.current || !graphReady) {
      return;
    }

    const { width, height } = getContainerSize(containerRef.current);

    try {
      graphRef.current.setLayout(getKnowledgeLayoutConfig(layoutType, width, height));
      await graphRef.current.layout();
      graphRef.current.fitView();
    } catch (error) {
      console.error("[KnowledgeGraph] failed to switch layout", error);
      message.error("Failed to switch graph layout");
    }
  };

  const handleModeChange = (mode: GraphViewMode) => {
    if (mode === "interactive") {
      prefetchGraphRuntime();
    }
    startTransition(() => {
      setViewMode(mode);
    });
  };

  const togglePinFocusedEntity = () => {
    if (!focusedExplorerEntity) {
      return;
    }
    setPinnedEntityIds((current) => {
      if (current.includes(focusedExplorerEntity.id)) {
        return current.filter((entityId) => entityId !== focusedExplorerEntity.id);
      }
      return [...current, focusedExplorerEntity.id].slice(-6);
    });
  };

  const handleExportExplorerSnapshot = () => {
    if (!focusedExplorerEntity) {
      return;
    }

    downloadKnowledgeSnapshot(
      JSON.stringify(
        {
          exported_at: new Date().toISOString(),
          knowledge_base_id: kbId,
          knowledge_base_name: kbName,
          focused_entity: focusedExplorerEntity,
          filters: {
            filterTypes,
            searchKeyword,
            explorerDirection,
            explorerHopDepth,
          },
          trail: trailEntities.map((entity) => ({
            id: entity.id,
            name: entity.name,
            type: entity.type,
          })),
          pinned_entities: pinnedEntities.map((entity) => ({
            id: entity.id,
            name: entity.name,
            type: entity.type,
          })),
          reachable_entities: reachableEntities.map(({ entity, depth }) => ({
            id: entity.id,
            name: entity.name,
            type: entity.type,
            depth,
          })),
          traversed_relationships: neighborhood.edges.map((item) => ({
            relationship_id: item.relationship.id,
            relation_type: item.relationship.relation_type,
            direction: item.directionLabel,
            depth: item.depth,
            counterpart_id: item.counterpartId,
            counterpart_name: item.counterpartName,
            counterpart_type: item.counterpartType,
          })),
          comparison: comparisonStats
            ? {
                comparison_entity: {
                  id: comparisonStats.comparisonEntity.id,
                  name: comparisonStats.comparisonEntity.name,
                  type: comparisonStats.comparisonEntity.type,
                },
                shared_entities: comparisonStats.sharedEntities,
                current_only_entities: comparisonStats.focusOnlyEntities,
                pinned_only_entities: comparisonStats.compareOnlyEntities,
                shared_relationships: comparisonStats.sharedEdges,
              }
            : null,
        },
        null,
        2,
      ),
      `knowledge-graph-explorer-${focusedExplorerEntity.id}.json`,
      "application/json",
    );
  };

  const handleCloseDetail = () => {
    setDetailPanelVisible(false);
    setSelectedEntity(null);
    setSelectedEntityNeighbors([]);
  };

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100%" }}>
        <Spin size="large" tip="Loading graph data..." />
      </div>
    );
  }

  if (entities.length === 0) {
    return (
      <div style={{ padding: 24 }}>
        {graphError ? (
          <Alert
            type="warning"
            showIcon
            message="Graph data unavailable"
            description={graphError}
            style={{ marginBottom: 16 }}
          />
        ) : null}
        <Empty
          description={`No graph data is available for ${kbName} yet. Check the GraphRAG extraction result or reprocess the documents.`}
          style={{ marginTop: 100 }}
        />
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", minHeight: 500 }}>
      <GraphToolbar
        statistics={statistics}
        entityTypes={entityTypes}
        filterTypes={filterTypes}
        graphReady={graphReady}
        currentLayout={currentLayout}
        onFilterChange={setFilterTypes}
        onSearch={setSearchKeyword}
        onLayoutChange={handleLayoutChange}
        onFitView={() => graphRef.current?.fitView()}
        onRefresh={loadGraphData}
      />
      <div style={{ padding: "12px 16px 0" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: 16,
            alignItems: "flex-start",
            flexWrap: "wrap",
          }}
        >
          <div>
            <Text strong>{VIEW_MODE_LABELS[viewMode]}</Text>
            <Paragraph style={{ marginBottom: 0 }}>{VIEW_MODE_COPY[viewMode]}</Paragraph>
          </div>
          <div style={modeSwitchStyle}>
            {(["summary", "explorer", "interactive"] as GraphViewMode[]).map((mode) => (
              <Button
                key={mode}
                type={viewMode === mode ? "primary" : "default"}
                onMouseEnter={mode === "interactive" ? prefetchGraphRuntime : undefined}
                onFocus={mode === "interactive" ? prefetchGraphRuntime : undefined}
                onClick={() => handleModeChange(mode)}
              >
                {VIEW_MODE_LABELS[mode]}
              </Button>
            ))}
          </div>
        </div>
      </div>
      {viewMode === "summary" ? (
        <div style={{ padding: 16, background: "#fafafa", borderRadius: 8, margin: 12 }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
            <Tag>{`Entities: ${statistics?.entity_count || entities.length}`}</Tag>
            <Tag>{`Relationships: ${statistics?.relationship_count || relationships.length}`}</Tag>
            {Object.entries(statistics?.entity_types || {}).map(([type, count]) => (
              <Tag key={type} color={getEntityTypeColor(type)}>
                {`${type}: ${count}`}
              </Tag>
            ))}
          </div>
          <div style={quickGridStyle}>
            <div>
              <Text strong>Key entities</Text>
              <div style={{ display: "grid", gap: 10, marginTop: 12 }}>
                {topEntities.map((entity) => (
                  <button
                    key={entity.id}
                    type="button"
                    style={{ ...quickCardStyle, cursor: "pointer" }}
                    onClick={() => void openEntityDetail(entity)}
                  >
                    <span style={{ fontWeight: 600 }}>{entity.name}</span>
                    <span style={{ color: "#5f6f84", fontSize: 12 }}>{entity.type}</span>
                  </button>
                ))}
              </div>
            </div>
            <div>
              <Text strong>Relationship highlights</Text>
              <div style={{ display: "grid", gap: 10, marginTop: 12 }}>
                {topRelationships.map((relationship) => (
                  <div key={relationship.id} style={quickCardStyle}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                      <span>{relationship.source_name}</span>
                      <Tag color="blue">{relationship.relation_type}</Tag>
                      <span>{relationship.target_name}</span>
                    </div>
                    {relationship.description ? (
                      <span style={{ color: "#5f6f84", fontSize: 12 }}>{relationship.description}</span>
                    ) : null}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : null}
      {viewMode === "explorer" ? (
        <div style={{ padding: 16, background: "#fafafa", borderRadius: 8, margin: 12 }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
            {trailEntities.length > 0 ? (
              trailEntities.map((entity) => (
                <Button
                  key={entity.id}
                  size="small"
                  type={focusedExplorerEntity?.id === entity.id ? "primary" : "default"}
                  onClick={() => setExplorerEntityId(entity.id)}
                >
                  {entity.name}
                </Button>
              ))
            ) : (
              <Tag>No trail yet</Tag>
            )}
            {trailEntities.length > 0 ? (
              <Button size="small" onClick={() => setExplorerTrail(focusedExplorerEntity ? [focusedExplorerEntity.id] : [])}>
                Clear trail
              </Button>
            ) : null}
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
            {(["all", "outgoing", "incoming"] as ExplorerDirection[]).map((direction) => (
              <Button
                key={direction}
                size="small"
                type={explorerDirection === direction ? "primary" : "default"}
                onClick={() => setExplorerDirection(direction)}
              >
                {direction === "all" ? "All directions" : direction}
              </Button>
            ))}
            {[1, 2].map((hop) => (
              <Button
                key={hop}
                size="small"
                type={explorerHopDepth === hop ? "primary" : "default"}
                onClick={() => setExplorerHopDepth(hop as 1 | 2)}
              >
                {`${hop}-hop`}
              </Button>
            ))}
            <Button size="small" type={isFocusedEntityPinned ? "primary" : "default"} onClick={togglePinFocusedEntity}>
              {isFocusedEntityPinned ? "Unpin current" : "Pin current"}
            </Button>
            {pinnedEntities.map((entity) => (
              <Button
                key={entity.id}
                size="small"
                type={focusedExplorerEntity?.id === entity.id ? "primary" : "default"}
                onClick={() => setExplorerEntityId(entity.id)}
              >
                {entity.name}
              </Button>
            ))}
            {pinnedEntities.length > 0 ? (
              <Button size="small" onClick={() => setPinnedEntityIds([])}>
                Clear pins
              </Button>
            ) : null}
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
            <Tag>{`Visible entities: ${filteredEntities.length}`}</Tag>
            <Tag>{`Neighborhood entities: ${reachableEntities.length}`}</Tag>
            <Tag>{`Traversed relationships: ${neighborhood.edges.length}`}</Tag>
          </div>
          <div style={explorerGridStyle}>
            <div>
              <Text strong>Entity explorer</Text>
              <div style={{ display: "grid", gap: 10, marginTop: 12 }}>
                {filteredEntities.slice(0, 18).map((entity) => (
                  <button
                    key={entity.id}
                    type="button"
                    style={{
                      ...quickCardStyle,
                      cursor: "pointer",
                      borderColor:
                        focusedExplorerEntity?.id === entity.id
                          ? "rgba(24, 144, 255, 0.35)"
                          : "rgba(16, 35, 58, 0.08)",
                      background:
                        focusedExplorerEntity?.id === entity.id ? "rgba(230, 244, 255, 0.88)" : "#fff",
                    }}
                    onClick={() => setExplorerEntityId(entity.id)}
                  >
                    <span style={{ fontWeight: 600 }}>{entity.name}</span>
                    <span style={{ color: "#5f6f84", fontSize: 12 }}>{entity.type}</span>
                  </button>
                ))}
                {filteredEntities.length === 0 ? (
                  <div style={quickCardStyle}>No entities match the current search and filter.</div>
                ) : null}
              </div>
            </div>
            <div>
              <Text strong>Neighborhood</Text>
              <div style={{ ...quickCardStyle, marginTop: 12, minHeight: 260 }}>
                {focusedExplorerEntity ? (
                  <>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        gap: 10,
                        width: "100%",
                        flexWrap: "wrap",
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: 600 }}>{focusedExplorerEntity.name}</div>
                        <div style={{ color: "#5f6f84", fontSize: 12 }}>{focusedExplorerEntity.type}</div>
                      </div>
                      <Space size="small">
                        <Button size="small" onClick={handleExportExplorerSnapshot}>
                          Export snapshot
                        </Button>
                        <Button size="small" onClick={() => void openEntityDetail(focusedExplorerEntity)}>
                          Open detail
                        </Button>
                      </Space>
                    </div>
                    {focusedExplorerEntity.description ? (
                      <Paragraph style={{ marginBottom: 8 }}>{focusedExplorerEntity.description}</Paragraph>
                    ) : null}
                    <Text strong>Reachable entities</Text>
                    <div style={{ display: "grid", gap: 10, width: "100%", marginTop: 10 }}>
                      {reachableEntities.slice(0, 8).map(({ entity, depth }) => (
                        <button
                          key={entity.id}
                          type="button"
                          style={{ ...quickCardStyle, width: "100%", cursor: "pointer" }}
                          onClick={() => setExplorerEntityId(entity.id)}
                        >
                          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                            <span style={{ fontWeight: 600 }}>{entity.name}</span>
                            <Tag color={depth === 1 ? "blue" : "gold"}>{`${depth}-hop`}</Tag>
                          </div>
                          <span style={{ color: "#5f6f84", fontSize: 12 }}>{entity.type}</span>
                        </button>
                      ))}
                      {reachableEntities.length === 0 ? (
                        <Text type="secondary">No reachable entities for the current explorer filter.</Text>
                      ) : null}
                    </div>
                    {comparisonStats ? (
                      <>
                        <Text strong style={{ marginTop: 6 }}>
                          {`Compare vs ${comparisonStats.comparisonEntity.name}`}
                        </Text>
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, width: "100%", marginTop: 10 }}>
                          <div style={quickCardStyle}>
                            <span style={{ color: "#5f6f84", fontSize: 12 }}>Shared entities</span>
                            <strong>{comparisonStats.sharedEntities}</strong>
                          </div>
                          <div style={quickCardStyle}>
                            <span style={{ color: "#5f6f84", fontSize: 12 }}>Shared relationships</span>
                            <strong>{comparisonStats.sharedEdges}</strong>
                          </div>
                          <div style={quickCardStyle}>
                            <span style={{ color: "#5f6f84", fontSize: 12 }}>Current-only entities</span>
                            <strong>{comparisonStats.focusOnlyEntities}</strong>
                          </div>
                          <div style={quickCardStyle}>
                            <span style={{ color: "#5f6f84", fontSize: 12 }}>Pinned-only entities</span>
                            <strong>{comparisonStats.compareOnlyEntities}</strong>
                          </div>
                        </div>
                      </>
                    ) : null}
                    <Text strong style={{ marginTop: 6 }}>
                      Traversed relationships
                    </Text>
                    <div style={{ display: "grid", gap: 10, width: "100%", marginTop: 10 }}>
                      {neighborhood.edges.slice(0, 10).map((item) => (
                        <button
                          key={item.relationship.id}
                          type="button"
                          style={{
                            ...quickCardStyle,
                            width: "100%",
                            cursor: "pointer",
                            background: "rgba(16, 35, 58, 0.04)",
                          }}
                          onClick={() => setExplorerEntityId(item.counterpartId)}
                        >
                          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                            <span style={{ fontWeight: 600 }}>{item.counterpartName}</span>
                            <Tag color={item.directionLabel === "Outgoing" ? "blue" : "green"}>
                              {`${item.directionLabel} / ${item.depth}-hop`}
                            </Tag>
                          </div>
                          <span style={{ color: "#5f6f84", fontSize: 12 }}>
                            {item.counterpartType} / {item.relationship.relation_type}
                            {item.relationship.description ? ` / ${item.relationship.description}` : ""}
                          </span>
                        </button>
                      ))}
                      {neighborhood.edges.length === 0 ? (
                        <Text type="secondary">No traversed relationships for this entity.</Text>
                      ) : null}
                    </div>
                  </>
                ) : (
                  <Text type="secondary">Select an entity to inspect the local neighborhood.</Text>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : null}
      {graphError ? (
        <Alert banner type="warning" showIcon message={graphError} style={{ borderRadius: 0 }} />
      ) : null}
      {viewMode === "interactive" ? (
        <div
          ref={containerRef}
          style={{ flex: 1, minHeight: 420, position: "relative", background: "#fafafa", borderRadius: 8, margin: 12 }}
        />
      ) : null}
      <EntityDetailPanel
        visible={detailPanelVisible}
        entity={selectedEntity}
        neighbors={selectedEntityNeighbors}
        onClose={handleCloseDetail}
      />
    </div>
  );
};

export default KnowledgeGraph;
