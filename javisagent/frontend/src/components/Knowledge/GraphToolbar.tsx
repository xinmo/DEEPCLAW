import React, { useState } from 'react';
import { Space, Select, Input, Button, Tooltip, Tag, Statistic, Card } from 'antd';
import {
  SearchOutlined,
  ReloadOutlined,
  FullscreenOutlined,
  ApartmentOutlined,
  NodeIndexOutlined,
  RadarChartOutlined,
  AppstoreOutlined,
} from '@ant-design/icons';
import type { GraphStatistics } from '../../types/knowledge';
import { getEntityTypeColor } from '../../types/knowledge';

interface GraphToolbarProps {
  statistics: GraphStatistics | null;
  entityTypes: string[];
  filterTypes: string[];
  graphReady: boolean;
  onFilterChange: (types: string[]) => void;
  onSearch: (keyword: string) => void;
  onLayoutChange: (layout: string) => void;
  onFitView: () => void;
  onRefresh: () => void;
}

const LAYOUT_OPTIONS = [
  { value: 'force', label: '力导向', icon: <NodeIndexOutlined /> },
  { value: 'circular', label: '环形', icon: <RadarChartOutlined /> },
  { value: 'grid', label: '网格', icon: <AppstoreOutlined /> },
  { value: 'radial', label: '辐射', icon: <ApartmentOutlined /> },
];

const GraphToolbar: React.FC<GraphToolbarProps> = ({
  statistics,
  entityTypes,
  filterTypes,
  graphReady,
  onFilterChange,
  onSearch,
  onLayoutChange,
  onFitView,
  onRefresh,
}) => {
  const [searchValue, setSearchValue] = useState('');
  const [currentLayout, setCurrentLayout] = useState('force');

  const handleSearch = () => {
    console.log(`[GraphToolbar] 执行搜索 | keyword=${searchValue}`);
    onSearch(searchValue);
  };

  const handleLayoutChange = (value: string) => {
    console.log(`[GraphToolbar] 切换布局 | layout=${value}`);
    setCurrentLayout(value);
    onLayoutChange(value);
  };

  return (
    <div style={{ padding: '12px 16px', background: '#fff', borderBottom: '1px solid #f0f0f0' }}>
      {/* 统计信息 */}
      {statistics && (
        <div style={{ display: 'flex', gap: 24, marginBottom: 12 }}>
          <Card size="small" style={{ minWidth: 100 }}>
            <Statistic title="实体数" value={statistics.entity_count} valueStyle={{ fontSize: 20 }} />
          </Card>
          <Card size="small" style={{ minWidth: 100 }}>
            <Statistic title="关系数" value={statistics.relationship_count} valueStyle={{ fontSize: 20 }} />
          </Card>
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 4 }}>
            {Object.entries(statistics.entity_types).map(([type, count]) => (
              <Tag
                key={type}
                color={getEntityTypeColor(type)}
                style={{ cursor: 'pointer' }}
                onClick={() => {
                  if (filterTypes.includes(type)) {
                    onFilterChange(filterTypes.filter(t => t !== type));
                  } else {
                    onFilterChange([...filterTypes, type]);
                  }
                }}
              >
                {type}: {count}
              </Tag>
            ))}
          </div>
        </div>
      )}

      {/* 工具栏 */}
      <Space wrap>
        {/* 类型筛选 */}
        <Select
          mode="multiple"
          placeholder="筛选实体类型"
          style={{ minWidth: 200 }}
          value={filterTypes}
          onChange={onFilterChange}
          allowClear
          options={entityTypes.map(type => ({
            label: (
              <Space>
                <span
                  style={{
                    display: 'inline-block',
                    width: 12,
                    height: 12,
                    borderRadius: '50%',
                    background: getEntityTypeColor(type),
                  }}
                />
                {type}
              </Space>
            ),
            value: type,
          }))}
        />

        {/* 搜索 */}
        <Input.Search
          placeholder="搜索实体名称"
          style={{ width: 200 }}
          value={searchValue}
          onChange={e => setSearchValue(e.target.value)}
          onSearch={handleSearch}
          enterButton={<SearchOutlined />}
          allowClear
          onClear={() => {
            setSearchValue('');
            onSearch('');
          }}
        />

        {/* 布局切换 */}
        <Select
          value={currentLayout}
          onChange={handleLayoutChange}
          style={{ width: 120 }}
          disabled={!graphReady}
          options={LAYOUT_OPTIONS.map(opt => ({
            label: (
              <Space>
                {opt.icon}
                {opt.label}
              </Space>
            ),
            value: opt.value,
          }))}
        />

        {/* 适应画布 */}
        <Tooltip title="适应画布">
          <Button icon={<FullscreenOutlined />} onClick={onFitView} disabled={!graphReady} />
        </Tooltip>

        {/* 刷新 */}
        <Tooltip title="刷新数据">
          <Button icon={<ReloadOutlined />} onClick={onRefresh} />
        </Tooltip>
      </Space>
    </div>
  );
};

export default GraphToolbar;
