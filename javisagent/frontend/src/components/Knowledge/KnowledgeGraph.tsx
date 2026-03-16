import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Graph } from '@antv/g6';
import { Alert, Empty, Spin, message } from 'antd';
import { knowledgeApi } from '../../services/knowledgeApi';
import type { GraphEntity, GraphRelationship, GraphStatistics } from '../../types/knowledge';
import { getEntityTypeColor } from '../../types/knowledge';
import GraphToolbar from './GraphToolbar';
import EntityDetailPanel from './EntityDetailPanel';

interface KnowledgeGraphProps {
  kbId: string;
  kbName: string;
}

interface GraphNeighbor {
  entity: { id: string; name: string; type: string; description?: string };
  relation: { type: string; direction: string; description?: string; weight?: number };
  hop: number;
}

interface GraphClickEvent {
  target?: {
    id?: string;
    config?: { id?: string };
    attributes?: { id?: string };
  };
  view?: { id?: string };
  item?: { id?: string };
}

const DEFAULT_WIDTH = 800;
const DEFAULT_HEIGHT = 520;

const getContainerSize = (container: HTMLDivElement | null) => ({
  width: Math.max(Math.round(container?.clientWidth || 0), DEFAULT_WIDTH),
  height: Math.max(Math.round(container?.clientHeight || 0), DEFAULT_HEIGHT),
});

const getShortLabel = (name: string) => (name.length > 10 ? `${name.slice(0, 10)}...` : name);

const getClickedNodeId = (evt: GraphClickEvent): string | undefined =>
  evt?.target?.id ??
  evt?.view?.id ??
  evt?.item?.id ??
  evt?.target?.config?.id ??
  evt?.target?.attributes?.id;

const KnowledgeGraph: React.FC<KnowledgeGraphProps> = ({ kbId, kbName }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<Graph | null>(null);
  const resizeObserverRef = useRef<ResizeObserver | null>(null);

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
  const [searchKeyword, setSearchKeyword] = useState('');

  const loadGraphData = useCallback(async () => {
    setLoading(true);
    setGraphError(null);

    try {
      const [stats, ents, rels] = await Promise.all([
        knowledgeApi.getGraphStatistics(kbId),
        knowledgeApi.getGraphEntities(kbId, undefined, 500),
        knowledgeApi.getGraphRelationships(kbId, 1000),
      ]);

      setStatistics(stats);
      setEntities(ents);
      setRelationships(rels);
    } catch (error) {
      console.error('[KnowledgeGraph] 加载图谱数据失败:', error);
      setStatistics(null);
      setEntities([]);
      setRelationships([]);
      setGraphError('加载图谱数据失败，请检查后端图谱接口或刷新后重试');
      message.error('加载图谱数据失败');
    } finally {
      setLoading(false);
    }
  }, [kbId]);

  useEffect(() => {
    loadGraphData();
  }, [loadGraphData]);

  const graphData = useMemo(() => {
    let filteredEntities = entities;

    if (filterTypes.length > 0) {
      filteredEntities = filteredEntities.filter((entity) => filterTypes.includes(entity.type));
    }

    if (searchKeyword.trim()) {
      const keyword = searchKeyword.trim().toLowerCase();
      filteredEntities = filteredEntities.filter((entity) => entity.name.toLowerCase().includes(keyword));
    }

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
            labelPlacement: 'bottom',
            labelFontSize: 11,
          },
        };
      }),
      edges: relationships
        .filter((relationship) => entityIds.has(relationship.source_entity_id) && entityIds.has(relationship.target_entity_id))
        .map((relationship) => ({
          id: relationship.id,
          source: relationship.source_entity_id,
          target: relationship.target_entity_id,
          data: {
            relationType: relationship.relation_type,
            description: relationship.description,
          },
          style: {
            stroke: '#C0C4CC',
            lineWidth: 1,
            endArrow: true,
            labelText: relationship.relation_type,
            labelFontSize: 10,
            labelFill: '#666',
          },
        })),
    };
  }, [entities, relationships, filterTypes, searchKeyword]);

  useEffect(() => {
    const container = containerRef.current;

    resizeObserverRef.current?.disconnect();
    resizeObserverRef.current = null;

    if (graphRef.current) {
      graphRef.current.destroy();
      graphRef.current = null;
    }

    setGraphReady(false);

    if (!container || loading || graphData.nodes.length === 0) {
      return;
    }

    let disposed = false;
    const { width, height } = getContainerSize(container);
    const graph = new Graph({
      container,
      width,
      height,
      data: graphData,
      autoFit: 'view',
      padding: [24, 24, 24, 24],
      layout: {
        type: 'force',
        preventOverlap: true,
        nodeSize: 40,
        linkDistance: 120,
        nodeStrength: -80,
        edgeStrength: 0.5,
        damping: 0.9,
        maxIteration: 300,
        center: [width / 2, height / 2],
      },
      node: {
        type: 'circle',
      },
      edge: {
        type: 'line',
      },
      behaviors: ['drag-canvas', 'zoom-canvas', 'drag-node', 'click-select'],
    });

    graph.on('node:click', async (evt: GraphClickEvent) => {
      const nodeId = getClickedNodeId(evt);
      if (!nodeId) return;

      const entity = entities.find((item) => item.id === nodeId);
      if (!entity) return;

      setSelectedEntity(entity);
      setDetailPanelVisible(true);

      try {
        const detail = await knowledgeApi.getGraphEntityDetail(kbId, nodeId, 1);
        setSelectedEntityNeighbors(detail.neighbors);
      } catch (error) {
        console.error('[KnowledgeGraph] 加载实体详情失败:', error);
        setSelectedEntityNeighbors([]);
      }
    });

    const renderGraph = async () => {
      try {
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
      } catch (error) {
        console.error('[KnowledgeGraph] 图渲染失败:', error);
        setGraphReady(false);
        setGraphError('图谱渲染失败，请刷新重试');
        message.error('图谱渲染失败');
        graph.destroy();
      }
    };

    renderGraph();

    const observer = new ResizeObserver((entries) => {
      if (!graphRef.current || disposed) return;

      const rect = entries[0]?.contentRect;
      const nextWidth = Math.max(Math.round(rect?.width || container.clientWidth || 0), DEFAULT_WIDTH);
      const nextHeight = Math.max(Math.round(rect?.height || container.clientHeight || 0), DEFAULT_HEIGHT);

      graphRef.current.resize(nextWidth, nextHeight);
      graphRef.current.fitView();
    });

    observer.observe(container);
    resizeObserverRef.current = observer;

    return () => {
      disposed = true;
      observer.disconnect();
      resizeObserverRef.current = null;
      if (graphRef.current === graph) {
        graphRef.current = null;
      }
      graph.destroy();
    };
  }, [entities, graphData, kbId, loading]);

  useEffect(() => {
    return () => {
      resizeObserverRef.current?.disconnect();
      resizeObserverRef.current = null;
      if (graphRef.current) {
        graphRef.current.destroy();
        graphRef.current = null;
      }
    };
  }, []);

  const handleFilterChange = (types: string[]) => {
    setFilterTypes(types);
  };

  const handleSearch = (keyword: string) => {
    setSearchKeyword(keyword);
  };

  const handleLayoutChange = async (layoutType: string) => {
    if (!graphRef.current || !graphReady) {
      return;
    }

    const { width, height } = getContainerSize(containerRef.current);
    const layoutConfig: Record<string, object> = {
      force: {
        type: 'force',
        preventOverlap: true,
        nodeSize: 40,
        linkDistance: 120,
        damping: 0.9,
        maxIteration: 300,
        center: [width / 2, height / 2],
      },
      circular: {
        type: 'circular',
        center: [width / 2, height / 2],
      },
      grid: {
        type: 'grid',
        center: [width / 2, height / 2],
      },
      radial: {
        type: 'radial',
        unitRadius: 80,
        center: [width / 2, height / 2],
      },
    };

    try {
      graphRef.current.setLayout(layoutConfig[layoutType] || layoutConfig.force);
      await graphRef.current.layout();
      graphRef.current.fitView();
    } catch (error) {
      console.error('[KnowledgeGraph] 布局切换失败:', error);
      message.error('布局切换失败');
    }
  };

  const handleFitView = () => {
    graphRef.current?.fitView();
  };

  const handleCloseDetail = () => {
    setDetailPanelVisible(false);
    setSelectedEntity(null);
    setSelectedEntityNeighbors([]);
  };

  const entityTypes = statistics?.entity_types ? Object.keys(statistics.entity_types) : [];

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <Spin size="large" tip="加载图谱数据中..." />
      </div>
    );
  }

  if (entities.length === 0) {
    return (
      <div style={{ padding: 24 }}>
        {graphError && (
          <Alert
            type="warning"
            showIcon
            message="图谱数据不可用"
            description={graphError}
            style={{ marginBottom: 16 }}
          />
        )}
        <Empty
            description={`暂无图谱数据。若 ${kbName} 已显示文档完成但这里为空，请检查 GraphRAG 抽取结果或后端日志。`}
          style={{ marginTop: 100 }}
        />
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 500 }}>
      <GraphToolbar
        statistics={statistics}
        entityTypes={entityTypes}
        filterTypes={filterTypes}
        graphReady={graphReady}
        onFilterChange={handleFilterChange}
        onSearch={handleSearch}
        onLayoutChange={handleLayoutChange}
        onFitView={handleFitView}
        onRefresh={loadGraphData}
      />
      {graphError && (
        <Alert
          banner
          type="warning"
          showIcon
          message={graphError}
          style={{ borderRadius: 0 }}
        />
      )}
      <div
        ref={containerRef}
        style={{ flex: 1, minHeight: 420, position: 'relative', background: '#fafafa', borderRadius: 8 }}
      />
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
