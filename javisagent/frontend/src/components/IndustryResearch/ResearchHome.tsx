import React, { useState } from "react";
import { Button, Card, Progress, Radio, Tag, Tooltip, Typography } from "antd";
import { EyeOutlined, ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import type { ResearchDepth, ResearchHistory } from "../../types/industryResearch";

const { Title, Text } = Typography;

const HOT_TOPICS = ["半导体", "新能源汽车", "创新药", "AI算力", "锂电池", "光伏"];

const DEPTH_OPTIONS: { value: ResearchDepth; label: string; desc: string }[] = [
  { value: "quick", label: "快速概览", desc: "~3分钟，产业链骨架 + 主要玩家" },
  { value: "standard", label: "标准研究", desc: "~8分钟，完整图谱 + 各环节主要企业" },
  { value: "deep", label: "深度研究", desc: "~20分钟，完整图谱 + 每环节财务对比 + 上游原材料价格" },
];

const INDUSTRY_ICONS: Record<string, string> = {
  半导体: "🏭",
  新能源汽车: "🚗",
  创新药: "💊",
  AI算力: "🖥️",
  锂电池: "🔋",
  光伏: "☀️",
};

interface ResearchHomeProps {
  history: ResearchHistory[];
  loading: boolean;
  onStart: (query: string, depth: ResearchDepth) => void;
  onReview: (id: string) => void;
}

const ResearchHome: React.FC<ResearchHomeProps> = ({ history, loading, onStart, onReview }) => {
  const [query, setQuery] = useState("");
  const [depth, setDepth] = useState<ResearchDepth>("standard");

  const handleSearch = () => {
    if (!query.trim()) return;
    onStart(query.trim(), depth);
  };

  return (
    <div style={{ height: "100%", overflowY: "auto", background: "#f5f7fa" }}>
      {/* Hero search area */}
      <div
        style={{
          height: "40vh",
          minHeight: 280,
          background: "linear-gradient(135deg, #0d1117 0%, #161b22 50%, #1a2332 100%)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "32px 24px",
        }}
      >
        <Title level={2} style={{ color: "#fff", marginBottom: 8 }}>
          AI 产业研究室
        </Title>
        <Text style={{ color: "rgba(255,255,255,0.6)", marginBottom: 24 }}>
          输入行业或个股，AI 多智能体自动构建产业链图谱
        </Text>

        <div style={{ width: "100%", maxWidth: 600, marginBottom: 16 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              background: "rgba(255,255,255,0.1)",
              border: "1px solid rgba(255,255,255,0.2)",
              borderRadius: 8,
              padding: "8px 16px",
              gap: 8,
            }}
          >
            <SearchOutlined style={{ color: "rgba(255,255,255,0.4)", fontSize: 16 }} />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="输入行业（半导体）或个股（宁德时代/300750）"
              style={{
                flex: 1,
                background: "transparent",
                border: "none",
                outline: "none",
                color: "#fff",
                fontSize: 15,
              }}
            />
            <Button
              type="primary"
              size="small"
              loading={loading}
              onClick={handleSearch}
              disabled={!query.trim()}
            >
              开始研究
            </Button>
          </div>
        </div>

        <Radio.Group
          value={depth}
          onChange={(e) => setDepth(e.target.value as ResearchDepth)}
          style={{ marginBottom: 16 }}
        >
          {DEPTH_OPTIONS.map((opt) => (
            <Tooltip key={opt.value} title={opt.desc}>
              <Radio.Button
                value={opt.value}
                style={{
                  background: "transparent",
                  borderColor: "rgba(255,255,255,0.3)",
                  color: "rgba(255,255,255,0.8)",
                }}
              >
                {opt.label}
              </Radio.Button>
            </Tooltip>
          ))}
        </Radio.Group>

        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "center" }}>
          <Text style={{ color: "rgba(255,255,255,0.4)" }}>热门：</Text>
          {HOT_TOPICS.map((t) => (
            <Tag
              key={t}
              onClick={() => setQuery(t)}
              style={{
                cursor: "pointer",
                background: "rgba(255,255,255,0.1)",
                border: "1px solid rgba(255,255,255,0.2)",
                color: "rgba(255,255,255,0.8)",
              }}
            >
              {t}
            </Tag>
          ))}
        </div>
      </div>

      {/* History cards */}
      {history.length > 0 && (
        <div style={{ padding: "32px 24px" }}>
          <Title level={4} style={{ marginBottom: 16 }}>
            历史研究项目
          </Title>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
              gap: 16,
            }}
          >
            {history.map((item) => (
              <Card key={item.id} hoverable size="small" style={{ borderRadius: 8 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                  <span style={{ fontSize: 24 }}>{INDUSTRY_ICONS[item.query] ?? "🔬"}</span>
                  <div>
                    <Text strong>{item.query}</Text>
                    <br />
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {item.nodeCount ?? 0} 层环节 · {item.companyCount ?? 0} 家企业
                    </Text>
                  </div>
                </div>
                {item.status === "running" ? (
                  <Progress percent={item.progress ?? 0} size="small" status="active" />
                ) : (
                  <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                    <Button
                      size="small"
                      icon={<EyeOutlined />}
                      onClick={() => onReview(item.id)}
                    >
                      查看图谱
                    </Button>
                    <Button size="small" icon={<ReloadOutlined />}>
                      更新
                    </Button>
                  </div>
                )}
                <Text type="secondary" style={{ fontSize: 11, marginTop: 4, display: "block" }}>
                  {item.createdAt ? new Date(item.createdAt).toLocaleDateString("zh-CN") : ""}
                </Text>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ResearchHome;
