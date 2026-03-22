import React, { useState } from "react";
import { AppstoreOutlined, ApartmentOutlined, FullscreenOutlined, NodeIndexOutlined, RadarChartOutlined, ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import { Button, Card, Input, Select, Space, Statistic, Tag, Tooltip } from "antd";

import type { GraphStatistics } from "../../types/knowledge";
import { getEntityTypeColor } from "../../types/knowledge";

interface GraphToolbarProps {
  statistics: GraphStatistics | null;
  entityTypes: string[];
  filterTypes: string[];
  graphReady: boolean;
  currentLayout: string;
  onFilterChange: (types: string[]) => void;
  onSearch: (keyword: string) => void;
  onLayoutChange: (layout: string) => void;
  onFitView: () => void;
  onRefresh: () => void;
}

const LAYOUT_OPTIONS = [
  { value: "force", label: "Force", icon: <NodeIndexOutlined /> },
  { value: "circular", label: "Circular", icon: <RadarChartOutlined /> },
  { value: "grid", label: "Grid", icon: <AppstoreOutlined /> },
  { value: "radial", label: "Radial", icon: <ApartmentOutlined /> },
];

const GraphToolbar: React.FC<GraphToolbarProps> = ({
  statistics,
  entityTypes,
  filterTypes,
  graphReady,
  currentLayout,
  onFilterChange,
  onSearch,
  onLayoutChange,
  onFitView,
  onRefresh,
}) => {
  const [searchValue, setSearchValue] = useState("");

  return (
    <div style={{ padding: "12px 16px", background: "#fff", borderBottom: "1px solid #f0f0f0" }}>
      {statistics ? (
        <div style={{ display: "flex", gap: 24, marginBottom: 12 }}>
          <Card size="small" style={{ minWidth: 108 }}>
            <Statistic title="Entities" value={statistics.entity_count} valueStyle={{ fontSize: 20 }} />
          </Card>
          <Card size="small" style={{ minWidth: 108 }}>
            <Statistic title="Relationships" value={statistics.relationship_count} valueStyle={{ fontSize: 20 }} />
          </Card>
          <div style={{ flex: 1, display: "flex", alignItems: "center", flexWrap: "wrap", gap: 6 }}>
            {Object.entries(statistics.entity_types).map(([type, count]) => (
              <Tag
                key={type}
                color={getEntityTypeColor(type)}
                style={{ cursor: "pointer" }}
                onClick={() => {
                  if (filterTypes.includes(type)) {
                    onFilterChange(filterTypes.filter((item) => item !== type));
                  } else {
                    onFilterChange([...filterTypes, type]);
                  }
                }}
              >
                {`${type}: ${count}`}
              </Tag>
            ))}
          </div>
        </div>
      ) : null}
      <Space wrap>
        <Select
          mode="multiple"
          placeholder="Filter entity types"
          style={{ minWidth: 220 }}
          value={filterTypes}
          onChange={onFilterChange}
          allowClear
          options={entityTypes.map((type) => ({
            label: (
              <Space>
                <span
                  style={{
                    display: "inline-block",
                    width: 12,
                    height: 12,
                    borderRadius: "50%",
                    background: getEntityTypeColor(type),
                  }}
                />
                {type}
              </Space>
            ),
            value: type,
          }))}
        />
        <Input.Search
          placeholder="Search entities"
          style={{ width: 220 }}
          value={searchValue}
          onChange={(event) => setSearchValue(event.target.value)}
          onSearch={onSearch}
          enterButton={<SearchOutlined />}
          allowClear
        />
        <Select
          value={currentLayout}
          onChange={onLayoutChange}
          style={{ width: 132 }}
          disabled={!graphReady}
          options={LAYOUT_OPTIONS.map((option) => ({
            label: (
              <Space>
                {option.icon}
                {option.label}
              </Space>
            ),
            value: option.value,
          }))}
        />
        <Tooltip title="Fit graph to canvas">
          <Button icon={<FullscreenOutlined />} onClick={onFitView} disabled={!graphReady} />
        </Tooltip>
        <Tooltip title="Refresh graph data">
          <Button
            icon={<ReloadOutlined />}
            onClick={() => {
              setSearchValue("");
              onSearch("");
              onRefresh();
            }}
          />
        </Tooltip>
      </Space>
    </div>
  );
};

export default GraphToolbar;
