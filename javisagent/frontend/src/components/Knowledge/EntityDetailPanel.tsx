import React from "react";
import { ArrowLeftOutlined, ArrowRightOutlined } from "@ant-design/icons";
import { Descriptions, Divider, Drawer, Empty, List, Tag, Typography } from "antd";

import type { GraphEntity } from "../../types/knowledge";
import { getEntityTypeColor } from "../../types/knowledge";

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

const { Paragraph, Text } = Typography;

const EntityDetailPanel: React.FC<EntityDetailPanelProps> = ({
  visible,
  entity,
  neighbors,
  onClose,
}) => {
  if (!entity) {
    return null;
  }

  const outgoingRelations = neighbors.filter((item) => item.relation.direction === "out");
  const incomingRelations = neighbors.filter((item) => item.relation.direction === "in");

  return (
    <Drawer
      title={
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span
            style={{
              display: "inline-block",
              width: 16,
              height: 16,
              borderRadius: "50%",
              background: getEntityTypeColor(entity.type),
            }}
          />
          <span>{entity.name}</span>
          <Tag color={getEntityTypeColor(entity.type)}>{entity.type}</Tag>
        </div>
      }
      placement="right"
      width={420}
      open={visible}
      onClose={onClose}
      mask={false}
    >
      <Descriptions column={1} size="small" bordered>
        <Descriptions.Item label="Entity ID">
          <Text copyable style={{ fontSize: 12 }}>
            {entity.id}
          </Text>
        </Descriptions.Item>
        <Descriptions.Item label="Type">
          <Tag color={getEntityTypeColor(entity.type)}>{entity.type}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="Description">
          {entity.description || <Text type="secondary">No description available.</Text>}
        </Descriptions.Item>
        {entity.doc_id ? (
          <Descriptions.Item label="Source document">
            <Text style={{ fontSize: 12 }}>{entity.doc_id}</Text>
          </Descriptions.Item>
        ) : null}
      </Descriptions>
      {neighbors.length > 0 ? (
        <>
          {outgoingRelations.length > 0 ? (
            <>
              <Divider orientationMargin={0} style={{ fontSize: 13 }}>
                <ArrowRightOutlined /> Outgoing links ({outgoingRelations.length})
              </Divider>
              <List
                size="small"
                dataSource={outgoingRelations}
                renderItem={(item) => (
                  <List.Item>
                    <div style={{ width: "100%" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                        <Tag color="blue">{item.relation.type}</Tag>
                        <ArrowRightOutlined style={{ color: "#999" }} />
                        <span
                          style={{
                            display: "inline-block",
                            width: 10,
                            height: 10,
                            borderRadius: "50%",
                            background: getEntityTypeColor(item.entity.type),
                          }}
                        />
                        <Text strong>{item.entity.name}</Text>
                        <Tag style={{ fontSize: 10 }}>{item.entity.type}</Tag>
                      </div>
                      {item.relation.description ? (
                        <Paragraph
                          type="secondary"
                          style={{ fontSize: 12, marginTop: 4, marginBottom: 0 }}
                          ellipsis={{ rows: 2 }}
                        >
                          {item.relation.description}
                        </Paragraph>
                      ) : null}
                    </div>
                  </List.Item>
                )}
              />
            </>
          ) : null}
          {incomingRelations.length > 0 ? (
            <>
              <Divider orientationMargin={0} style={{ fontSize: 13 }}>
                <ArrowLeftOutlined /> Incoming links ({incomingRelations.length})
              </Divider>
              <List
                size="small"
                dataSource={incomingRelations}
                renderItem={(item) => (
                  <List.Item>
                    <div style={{ width: "100%" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                        <span
                          style={{
                            display: "inline-block",
                            width: 10,
                            height: 10,
                            borderRadius: "50%",
                            background: getEntityTypeColor(item.entity.type),
                          }}
                        />
                        <Text strong>{item.entity.name}</Text>
                        <Tag style={{ fontSize: 10 }}>{item.entity.type}</Tag>
                        <ArrowRightOutlined style={{ color: "#999" }} />
                        <Tag color="green">{item.relation.type}</Tag>
                      </div>
                      {item.relation.description ? (
                        <Paragraph
                          type="secondary"
                          style={{ fontSize: 12, marginTop: 4, marginBottom: 0 }}
                          ellipsis={{ rows: 2 }}
                        >
                          {item.relation.description}
                        </Paragraph>
                      ) : null}
                    </div>
                  </List.Item>
                )}
              />
            </>
          ) : null}
        </>
      ) : (
        <Empty description="No linked entities found." style={{ marginTop: 40 }} />
      )}
    </Drawer>
  );
};

export default EntityDetailPanel;
