import React from "react";
import { Card, Collapse, Tag, Typography } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  RobotOutlined,
} from "@ant-design/icons";

import type { ProcessStatus } from "../../types/claw";

const { Text, Paragraph } = Typography;

interface SubAgentCardProps {
  title: string;
  status: ProcessStatus;
  toolId?: string;
  transcript?: string;
  result?: string;
}

const SubAgentCard: React.FC<SubAgentCardProps> = ({
  title,
  status,
  toolId,
  transcript,
  result,
}) => {
  const icon =
    status === "running" ? (
      <LoadingOutlined style={{ color: "#722ed1" }} />
    ) : status === "success" || status === "completed" ? (
      <CheckCircleOutlined style={{ color: "#52c41a" }} />
    ) : status === "failed" ? (
      <CloseCircleOutlined style={{ color: "#ff4d4f" }} />
    ) : (
      <RobotOutlined style={{ color: "#722ed1" }} />
    );

  const tagColor =
    status === "running"
      ? "processing"
      : status === "success" || status === "completed"
        ? "success"
        : status === "failed"
          ? "error"
          : "default";

  return (
    <Card
      size="small"
      style={{
        marginBottom: 10,
        borderRadius: 12,
        background: "#faf7ff",
        borderColor: "#e8d9ff",
      }}
      bodyStyle={{ padding: 14 }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
        {icon}
        <Text strong>{title}</Text>
        <Tag color={tagColor}>{status}</Tag>
        {toolId && (
          <Text type="secondary" style={{ fontSize: 12 }}>
            {toolId}
          </Text>
        )}
      </div>

      {transcript && (
        <Paragraph
          style={{
            marginBottom: result ? 10 : 0,
            padding: 12,
            borderRadius: 8,
            background: "#ffffff",
            whiteSpace: "pre-wrap",
          }}
          ellipsis={!result ? { rows: 4, expandable: true, symbol: "展开" } : false}
        >
          {transcript}
        </Paragraph>
      )}

      {(transcript || result) && (
        <Collapse
          ghost
          items={[
            {
              key: "details",
              label: "查看过程",
              children: (
                <div style={{ display: "grid", gap: 14 }}>
                  {transcript && (
                    <div>
                      <Text strong style={{ display: "block", marginBottom: 6 }}>
                        过程转写
                      </Text>
                      <pre
                        style={{
                          margin: 0,
                          padding: 12,
                          borderRadius: 8,
                          background: "#ffffff",
                          whiteSpace: "pre-wrap",
                          wordBreak: "break-word",
                        }}
                      >
                        {transcript}
                      </pre>
                    </div>
                  )}
                  {result && (
                    <div>
                      <Text strong style={{ display: "block", marginBottom: 6 }}>
                        最终结果
                      </Text>
                      <pre
                        style={{
                          margin: 0,
                          padding: 12,
                          borderRadius: 8,
                          background: "#ffffff",
                          whiteSpace: "pre-wrap",
                          wordBreak: "break-word",
                        }}
                      >
                        {result}
                      </pre>
                    </div>
                  )}
                </div>
              ),
            },
          ]}
        />
      )}
    </Card>
  );
};

export default SubAgentCard;
