import React, { useEffect, useRef } from "react";
import { Progress, Tag, Typography } from "antd";
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  LoadingOutlined,
} from "@ant-design/icons";
import type { AgentStatus, LogEntry } from "../../types/industryResearch";

const { Text } = Typography;

const STATUS_ICON: Record<string, React.ReactNode> = {
  running: <LoadingOutlined style={{ color: "#1677ff" }} spin />,
  waiting: <ClockCircleOutlined style={{ color: "#8c8c8c" }} />,
  done: <CheckCircleOutlined style={{ color: "#52c41a" }} />,
};

const STATUS_TAG: Record<string, React.ReactNode> = {
  running: <Tag color="processing">运行中</Tag>,
  waiting: <Tag>等待中</Tag>,
  done: <Tag color="success">完成</Tag>,
};

interface AgentLogPanelProps {
  agents: AgentStatus[];
  logs: LogEntry[];
  progress: number;
  query: string;
}

const AgentLogPanel: React.FC<AgentLogPanelProps> = ({ agents, logs, progress, query }) => {
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div
      style={{
        padding: 16,
        height: "100%",
        overflowY: "auto",
        borderRight: "1px solid #f0f0f0",
        display: "flex",
        flexDirection: "column",
        gap: 12,
      }}
    >
      <div>
        <Text strong>{query} 产业链研究</Text>
        <Progress percent={progress} size="small" style={{ margin: "8px 0 0" }} />
      </div>

      <div>
        <Text type="secondary" style={{ fontSize: 12 }}>
          ─── 智能体团队 ───
        </Text>
        <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 8 }}>
          {agents.map((agent) => (
            <div
              key={agent.agentId}
              style={{
                padding: "8px 12px",
                background: "#fafafa",
                borderRadius: 6,
                border: "1px solid #f0f0f0",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 2 }}>
                {STATUS_ICON[agent.status] ?? STATUS_ICON.waiting}
                <Text strong style={{ flex: 1, fontSize: 13 }}>
                  {agent.name}
                </Text>
                {STATUS_TAG[agent.status]}
              </div>
              {agent.action && (
                <Text type="secondary" style={{ fontSize: 12, display: "block" }}>
                  {agent.action}
                </Text>
              )}
              {agent.detail && (
                <Text style={{ fontSize: 11, display: "block", color: "#1677ff" }}>
                  › {agent.detail}
                </Text>
              )}
            </div>
          ))}
          {agents.length === 0 && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              等待智能体启动...
            </Text>
          )}
        </div>
      </div>

      <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          ─── 实时日志 ───
        </Text>
        <div
          ref={logRef}
          style={{
            flex: 1,
            marginTop: 8,
            minHeight: 160,
            maxHeight: 240,
            overflowY: "auto",
            background: "#0d1117",
            borderRadius: 6,
            padding: "8px 10px",
            fontFamily: "monospace",
          }}
        >
          {logs.length === 0 ? (
            <Text style={{ fontSize: 11, color: "rgba(255,255,255,0.3)" }}>等待日志...</Text>
          ) : (
            logs.map((log, i) => (
              <div key={i} style={{ fontSize: 11, color: "rgba(255,255,255,0.7)", lineHeight: 1.6 }}>
                <span style={{ color: "#52c41a" }}>[{log.timestamp}]</span> {log.message}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default AgentLogPanel;
