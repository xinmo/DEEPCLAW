import React from "react";
import { Button, Card, Drawer, Progress, Tag, Typography } from "antd";
import { ExperimentOutlined } from "@ant-design/icons";
import type { GraphNode } from "../../types/industryResearch";

const { Title, Text, Paragraph } = Typography;

const COMPETITION_META: Record<string, { label: string; color: string }> = {
  domestic: { label: "国产机遇", color: "green" },
  foreign: { label: "外资垄断", color: "orange" },
  balanced: { label: "均衡竞争", color: "blue" },
};

interface NodeDrawerProps {
  node: GraphNode | null;
  open: boolean;
  onClose: () => void;
  onDeepResearch: (nodeId: string, nodeName: string) => void;
}

const NodeDrawer: React.FC<NodeDrawerProps> = ({ node, open, onClose, onDeepResearch }) => {
  if (!node) return null;
  const competition = COMPETITION_META[node.competitionType] ?? COMPETITION_META.balanced;

  return (
    <Drawer
      title={
        <>
          <Text strong>{node.label}</Text>{" "}
          <Tag color={competition.color}>{competition.label}</Tag>
        </>
      }
      placement="right"
      width={480}
      open={open}
      onClose={onClose}
      mask={false}
      styles={{ body: { padding: 16 } }}
    >
      <div style={{ marginBottom: 16 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          {node.layer}
        </Text>
        {node.nationalizationRate !== undefined && (
          <div style={{ marginTop: 8 }}>
            <Text style={{ fontSize: 12 }}>国产化率</Text>
            <Progress
              percent={Math.round(node.nationalizationRate * 100)}
              size="small"
              strokeColor="#52c41a"
            />
          </div>
        )}
      </div>

      {node.overview && (
        <div style={{ marginBottom: 16 }}>
          <Title level={5} style={{ marginBottom: 4 }}>
            环节概述
          </Title>
          <Paragraph style={{ fontSize: 13, marginBottom: 0 }}>{node.overview}</Paragraph>
        </div>
      )}

      {node.companies.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <Title level={5} style={{ marginBottom: 8 }}>
            核心企业
          </Title>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {node.companies.map((c, i) => (
              <Card key={i} size="small" style={{ minWidth: 100, textAlign: "center" }}>
                <Text strong style={{ display: "block", fontSize: 13 }}>
                  {c.name}
                </Text>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  {c.country}
                  {c.marketShare !== undefined
                    ? ` · ${Math.round(c.marketShare * 100)}%`
                    : ""}
                </Text>
                {c.exchange && (
                  <Tag color="blue" style={{ marginTop: 4, display: "block" }}>
                    {c.exchange}
                  </Tag>
                )}
              </Card>
            ))}
          </div>
        </div>
      )}

      {node.upstreamDeps && node.upstreamDeps.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <Title level={5} style={{ marginBottom: 8 }}>
            上游依赖
          </Title>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {node.upstreamDeps.map((d, i) => (
              <Tag key={i}>{d}</Tag>
            ))}
          </div>
        </div>
      )}

      {node.latestNews && node.latestNews.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <Title level={5} style={{ marginBottom: 8 }}>
            最新动态
          </Title>
          {node.latestNews.map((news, i) => (
            <div key={i} style={{ marginBottom: 4 }}>
              <Text style={{ fontSize: 13 }}>• {news}</Text>
            </div>
          ))}
        </div>
      )}

      <Card
        style={{
          background: "#f0f5ff",
          border: "1px solid #adc6ff",
          borderRadius: 8,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
          <ExperimentOutlined style={{ color: "#1677ff", fontSize: 18 }} />
          <Text strong>对此环节启动深度研究</Text>
        </div>
        <Text type="secondary" style={{ fontSize: 12, display: "block", marginBottom: 12 }}>
          AI 将生成投资级研究报告，包含市场格局、财务对比、竞争壁垒、投资风险
        </Text>
        <Button
          type="primary"
          block
          onClick={() => onDeepResearch(node.id, node.label)}
        >
          开始深度研究 →
        </Button>
      </Card>
    </Drawer>
  );
};

export default NodeDrawer;
