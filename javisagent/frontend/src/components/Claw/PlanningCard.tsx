import React from "react";
import { Card, List, Tag, Typography } from "antd";
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  SyncOutlined,
} from "@ant-design/icons";

import type { ProcessStatus } from "../../types/claw";

const { Text } = Typography;

interface PlanningCardProps {
  title: string;
  status: ProcessStatus;
  todos: Array<Record<string, unknown>>;
}

function todoStatusColor(status: string) {
  if (status === "completed") {
    return "success";
  }
  if (status === "in_progress") {
    return "processing";
  }
  return "default";
}

function todoStatusIcon(status: string) {
  if (status === "completed") {
    return <CheckCircleOutlined style={{ color: "#52c41a" }} />;
  }
  if (status === "in_progress") {
    return <SyncOutlined spin style={{ color: "#1677ff" }} />;
  }
  return <ClockCircleOutlined style={{ color: "#bfbfbf" }} />;
}

const PlanningCard: React.FC<PlanningCardProps> = ({ title, status, todos }) => {
  const completedCount = todos.filter((todo) => todo.status === "completed").length;
  const inProgressCount = todos.filter((todo) => todo.status === "in_progress").length;

  return (
    <Card
      size="small"
      style={{
        marginBottom: 10,
        borderRadius: 12,
        background: "#fffaf0",
        borderColor: "#ffe7ba",
      }}
      bodyStyle={{ padding: 14 }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
        <Text strong>{title}</Text>
        <Tag color="orange">{status}</Tag>
        <Tag>{todos.length} 项</Tag>
        {inProgressCount > 0 && <Tag color="processing">{inProgressCount} 进行中</Tag>}
        {completedCount > 0 && <Tag color="success">{completedCount} 已完成</Tag>}
      </div>

      <List
        size="small"
        dataSource={todos}
        renderItem={(todo, index) => {
          const todoRecord = todo as Record<string, unknown>;
          const label =
            typeof todoRecord.content === "string" ? todoRecord.content : `待办 ${index + 1}`;
          const todoStatus =
            typeof todoRecord.status === "string" ? todoRecord.status : "pending";

          return (
            <List.Item
              style={{
                padding: "10px 0",
                alignItems: "center",
                borderBottom: index === todos.length - 1 ? "none" : "1px solid #f0f0f0",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10, width: "100%" }}>
                {todoStatusIcon(todoStatus)}
                <Text
                  style={{
                    flex: 1,
                    color: todoStatus === "completed" ? "#8c8c8c" : "inherit",
                    textDecoration: todoStatus === "completed" ? "line-through" : "none",
                  }}
                >
                  {label}
                </Text>
                <Tag color={todoStatusColor(todoStatus)}>{todoStatus}</Tag>
              </div>
            </List.Item>
          );
        }}
      />
    </Card>
  );
};

export default PlanningCard;
