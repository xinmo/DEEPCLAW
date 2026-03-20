import React, { useRef, useState } from "react";
import { Button, Progress, Table, Tabs, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { ArrowLeftOutlined } from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import type { DeepResearchData, CompanyFinancial, RiskItem } from "../../types/industryResearch";

const { Text, Title } = Typography;

const RISK_COLORS: Record<RiskItem["level"], string> = {
  high: "#ff4d4f",
  medium: "#faad14",
  low: "#52c41a",
};

const RISK_ICONS: Record<RiskItem["level"], string> = {
  high: "🔴",
  medium: "🟡",
  low: "🟢",
};

interface DeepResearchProps {
  nodeName: string;
  report: string;
  deepData: DeepResearchData | null;
  progress: number;
  onBack: () => void;
}

const DeepResearch: React.FC<DeepResearchProps> = ({
  nodeName,
  report,
  deepData,
  progress,
  onBack,
}) => {
  const reportRef = useRef<HTMLDivElement>(null);
  const [activeTab, setActiveTab] = useState("market");

  const scrollToSection = (companyName: string) => {
    if (!reportRef.current) return;
    const headings = reportRef.current.querySelectorAll("h2, h3");
    for (const h of Array.from(headings)) {
      if (h.textContent?.includes(companyName)) {
        h.scrollIntoView({ behavior: "smooth", block: "start" });
        break;
      }
    }
  };

  const companyColumns: ColumnsType<CompanyFinancial> = [
    {
      title: "企业",
      dataIndex: "name",
      key: "name",
      render: (v: string) => (
        <Text
          strong
          style={{ cursor: "pointer", color: "#1677ff" }}
          onClick={() => scrollToSection(v)}
        >
          {v}
        </Text>
      ),
    },
    {
      title: "营收(亿)",
      dataIndex: "revenue",
      key: "revenue",
      sorter: (a, b) => a.revenue - b.revenue,
    },
    {
      title: "毛利率",
      dataIndex: "grossMargin",
      key: "grossMargin",
      render: (v: number) => `${v}%`,
      sorter: (a, b) => a.grossMargin - b.grossMargin,
    },
    {
      title: "PE",
      dataIndex: "pe",
      key: "pe",
      sorter: (a, b) => a.pe - b.pe,
    },
    {
      title: "国产化贡献",
      dataIndex: "domesticContribution",
      key: "domestic",
      render: (v: number) => "★".repeat(Math.min(Math.round(v), 5)),
    },
  ];

  const tabItems = [
    {
      key: "market",
      label: "市场格局",
      children: (
        <div>
          {(deepData?.marketShares ?? []).map((item, i) => (
            <div key={i} style={{ marginBottom: 8 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 2 }}>
                <Text>
                  {item.name} <Tag>{item.country}</Tag>
                </Text>
                <Text strong>{Math.round(item.share * 100)}%</Text>
              </div>
              <div style={{ height: 8, background: "#f0f0f0", borderRadius: 4 }}>
                <div
                  style={{
                    height: "100%",
                    width: `${Math.min(item.share * 100, 100)}%`,
                    background: "#1677ff",
                    borderRadius: 4,
                    transition: "width 0.5s",
                  }}
                />
              </div>
            </div>
          ))}
          {(deepData?.companies ?? []).length > 0 && (
            <div style={{ marginTop: 16 }}>
              <Title level={5}>A股上市公司对比</Title>
              <Table<CompanyFinancial>
                dataSource={deepData?.companies ?? []}
                columns={companyColumns}
                size="small"
                pagination={false}
                rowKey="ticker"
              />
            </div>
          )}
        </div>
      ),
    },
    {
      key: "materials",
      label: "原材料价格",
      children: (
        <div>
          {(deepData?.materials ?? []).length === 0 ? (
            <Text type="secondary">暂无原材料数据</Text>
          ) : (
            (deepData?.materials ?? []).map((m, i) => (
              <div key={i} style={{ marginBottom: 16 }}>
                <Text strong>{m.name}</Text>
                {m.analysis && (
                  <Text
                    type="secondary"
                    style={{ display: "block", marginTop: 4, fontSize: 12 }}
                  >
                    AI分析：{m.analysis}
                  </Text>
                )}
              </div>
            ))
          )}
        </div>
      ),
    },
    {
      key: "barriers",
      label: "竞争壁垒",
      children: (
        <div>
          {(deepData?.barriers ?? []).map((b, i) => (
            <div key={i} style={{ marginBottom: 10 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 2 }}>
                <Text>{b.dimension}</Text>
                <Text strong>
                  {"★".repeat(Math.min(b.score, 5))}
                  {"☆".repeat(Math.max(5 - b.score, 0))}
                </Text>
              </div>
              <div style={{ height: 6, background: "#f0f0f0", borderRadius: 3 }}>
                <div
                  style={{
                    height: "100%",
                    width: `${Math.min(b.score * 20, 100)}%`,
                    background: "#722ed1",
                    borderRadius: 3,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      ),
    },
    {
      key: "risks",
      label: "投资风险",
      children: (
        <div>
          {(deepData?.risks ?? []).map((r, i) => (
            <div
              key={i}
              style={{
                marginBottom: 8,
                padding: "8px 12px",
                background: "#fafafa",
                borderRadius: 6,
                borderLeft: `3px solid ${RISK_COLORS[r.level]}`,
              }}
            >
              <Text>
                {RISK_ICONS[r.level]} {r.description}
              </Text>
            </div>
          ))}
        </div>
      ),
    },
  ];

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
          返回图谱
        </Button>
        <Text strong>{nodeName} 深度研究</Text>
        <div style={{ flex: 1 }} />
        {progress < 100 && (
          <Progress percent={progress} size="small" style={{ width: 200 }} />
        )}
      </div>

      {/* Main content */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        {/* Left panel */}
        <div
          style={{
            width: "45%",
            borderRight: "1px solid #f0f0f0",
            overflowY: "auto",
            padding: 16,
            flexShrink: 0,
          }}
        >
          <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
        </div>

        {/* Right panel - Report */}
        <div
          ref={reportRef}
          style={{ flex: 1, overflowY: "auto", padding: 24 }}
        >
          {report ? (
            <div
              style={{
                lineHeight: 1.8,
                fontSize: 14,
              }}
            >
              <ReactMarkdown>{report}</ReactMarkdown>
            </div>
          ) : (
            <div style={{ textAlign: "center", marginTop: 60 }}>
              <Text type="secondary">
                {progress > 0 ? "AI 正在生成研究报告..." : "等待深度研究启动..."}
              </Text>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DeepResearch;
