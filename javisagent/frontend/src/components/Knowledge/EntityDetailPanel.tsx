import React from 'react';
import { Drawer, Descriptions, Tag, List, Typography, Empty, Divider } from 'antd';
import { ArrowRightOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import type { GraphEntity } from '../../types/knowledge';
import { getEntityTypeColor } from '../../types/knowledge';

interface EntityDetailPanelProps {
  visible: boolean;
  entity: GraphEntity | null;
  neighbors: Array<{
    entity: { id: string; name: string; type: string; description?: string };
    relation: { type: string; direction: string; description?: string; weight?: number };
    hop: number;
  }>;
  onClose: () => void;
}

const { Text, Paragraph } = Typography;

const EntityDetailPanel: React.FC<EntityDetailPanelProps> = ({
  visible,
  entity,
  neighbors,
  onClose,
}) => {
  if (!entity) return null;

  console.log(`[EntityDetailPanel] 显示实体详情 | name=${entity.name} | neighbors=${neighbors.length}`);

  // 按关系方向分组
  const outgoingRelations = neighbors.filter(n => n.relation.direction === 'out');
  const incomingRelations = neighbors.filter(n => n.relation.direction === 'in');

  return (
    <Drawer
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span
            style={{
              display: 'inline-block',
              width: 16,
              height: 16,
              borderRadius: '50%',
              background: getEntityTypeColor(entity.type),
            }}
          />
          <span>{entity.name}</span>
          <Tag color={getEntityTypeColor(entity.type)}>{entity.type}</Tag>
        </div>
      }
      placement="right"
      width={400}
      open={visible}
      onClose={onClose}
      mask={false}
    >
      {/* 基本信息 */}
      <Descriptions column={1} size="small" bordered>
        <Descriptions.Item label="实体ID">
          <Text copyable style={{ fontSize: 12 }}>{entity.id}</Text>
        </Descriptions.Item>
        <Descriptions.Item label="类型">
          <Tag color={getEntityTypeColor(entity.type)}>{entity.type}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="描述">
          {entity.description || <Text type="secondary">暂无描述</Text>}
        </Descriptions.Item>
        {entity.doc_id && (
          <Descriptions.Item label="来源文档">
            <Text style={{ fontSize: 12 }}>{entity.doc_id}</Text>
          </Descriptions.Item>
        )}
      </Descriptions>

      {/* 关系信息 */}
      {neighbors.length > 0 ? (
        <>
          {/* 出边关系 */}
          {outgoingRelations.length > 0 && (
            <>
              <Divider orientationMargin={0} style={{ fontSize: 13 }}>
                <ArrowRightOutlined /> 指向的实体 ({outgoingRelations.length})
              </Divider>
              <List
                size="small"
                dataSource={outgoingRelations}
                renderItem={item => (
                  <List.Item>
                    <div style={{ width: '100%' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                        <Tag color="blue">{item.relation.type}</Tag>
                        <ArrowRightOutlined style={{ color: '#999' }} />
                        <span
                          style={{
                            display: 'inline-block',
                            width: 10,
                            height: 10,
                            borderRadius: '50%',
                            background: getEntityTypeColor(item.entity.type),
                          }}
                        />
                        <Text strong>{item.entity.name}</Text>
                        <Tag style={{ fontSize: 10 }}>{item.entity.type}</Tag>
                      </div>
                      {item.relation.description && (
                        <Paragraph
                          type="secondary"
                          style={{ fontSize: 12, marginTop: 4, marginBottom: 0 }}
                          ellipsis={{ rows: 2 }}
                        >
                          {item.relation.description}
                        </Paragraph>
                      )}
                    </div>
                  </List.Item>
                )}
              />
            </>
          )}

          {/* 入边关系 */}
          {incomingRelations.length > 0 && (
            <>
              <Divider orientationMargin={0} style={{ fontSize: 13 }}>
                <ArrowLeftOutlined /> 指向该实体 ({incomingRelations.length})
              </Divider>
              <List
                size="small"
                dataSource={incomingRelations}
                renderItem={item => (
                  <List.Item>
                    <div style={{ width: '100%' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                        <span
                          style={{
                            display: 'inline-block',
                            width: 10,
                            height: 10,
                            borderRadius: '50%',
                            background: getEntityTypeColor(item.entity.type),
                          }}
                        />
                        <Text strong>{item.entity.name}</Text>
                        <Tag style={{ fontSize: 10 }}>{item.entity.type}</Tag>
                        <ArrowRightOutlined style={{ color: '#999' }} />
                        <Tag color="green">{item.relation.type}</Tag>
                      </div>
                      {item.relation.description && (
                        <Paragraph
                          type="secondary"
                          style={{ fontSize: 12, marginTop: 4, marginBottom: 0 }}
                          ellipsis={{ rows: 2 }}
                        >
                          {item.relation.description}
                        </Paragraph>
                      )}
                    </div>
                  </List.Item>
                )}
              />
            </>
          )}
        </>
      ) : (
        <Empty description="暂无关联实体" style={{ marginTop: 40 }} />
      )}
    </Drawer>
  );
};

export default EntityDetailPanel;
