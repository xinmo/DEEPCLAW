import React from "react";
import { Card, Collapse, Tag, Typography } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  RobotOutlined,
} from "@ant-design/icons";

import type { ProcessStatus, ToolCall } from "../../types/claw";
import ToolCallCard from "./ToolCallCard";

const { Text, Paragraph } = Typography;

interface SubAgentCardProps {
  title: string;
  status: ProcessStatus;
  toolId?: string;
  transcript?: string;
  result?: string;
  childTools?: ToolCall[];
}

function getChildToolSummary(tools: ToolCall[]) {
  const runningCount = tools.filter((tool) => tool.status === "running").length;
  const successCount = tools.filter((tool) => tool.status === "success").length;
  const failedCount = tools.filter((tool) => tool.status === "failed").length;
  return {
    total: tools.length,
    runningCount,
    successCount,
    failedCount,
  };
}

const SubAgentCard: React.FC<SubAgentCardProps> = ({
  title,
  status,
  toolId,
  transcript,
  result,
  childTools,
}) => {
  const nestedTools = Array.isArray(childTools) ? childTools : [];
  const hasDetails = Boolean(transcript || result);
  const childToolSummary = getChildToolSummary(nestedTools);

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
        {toolId ? (
          <Text type="secondary" style={{ fontSize: 12 }}>
            {toolId}
          </Text>
        ) : null}
      </div>

      {transcript ? (
        <Paragraph
          style={{
            marginBottom: nestedTools.length > 0 || result ? 12 : 0,
            padding: 12,
            borderRadius: 8,
            background: "#ffffff",
            whiteSpace: "pre-wrap",
          }}
          ellipsis={
            nestedTools.length > 0 || result
              ? { rows: 3, expandable: true, symbol: "展开" }
              : false
          }
        >
          {transcript}
        </Paragraph>
      ) : null}

      {nestedTools.length > 0 ? (
        <div style={{ marginBottom: hasDetails ? 12 : 0 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              flexWrap: "wrap",
              marginBottom: 10,
            }}
          >
            <Text strong>工具活动</Text>
            <Tag>{`${childToolSummary.total} 个工具`}</Tag>
            {childToolSummary.runningCount > 0 ? (
              <Tag color="processing">{`${childToolSummary.runningCount} 进行中`}</Tag>
            ) : null}
            {childToolSummary.successCount > 0 ? (
              <Tag color="success">{`${childToolSummary.successCount} 完成`}</Tag>
            ) : null}
            {childToolSummary.failedCount > 0 ? (
              <Tag color="error">{`${childToolSummary.failedCount} 失败`}</Tag>
            ) : null}
          </div>
          <div style={{ display: "grid", gap: 10 }}>
            {nestedTools.map((tool) => (
              <ToolCallCard key={tool.id} toolCall={tool} />
            ))}
          </div>
        </div>
      ) : null}

      {hasDetails ? (
        <Collapse
          ghost
          defaultActiveKey={status === "running" ? ["details"] : []}
          items={[
            {
              key: "details",
              label: result ? "执行详情" : "过程记录",
              children: (
                <div style={{ display: "grid", gap: 14 }}>
                  {transcript ? (
                    <div>
                      <Text strong style={{ display: "block", marginBottom: 6 }}>
                        过程记录
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
                  ) : null}

                  {result ? (
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
                  ) : null}
                </div>
              ),
            },
          ]}
        />
      ) : null}
    </Card>
  );
};

export default SubAgentCard;
