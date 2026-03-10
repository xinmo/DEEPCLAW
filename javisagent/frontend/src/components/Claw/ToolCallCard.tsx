import React, { useState } from 'react';
import { Card, Tag, Collapse, Typography } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  ToolOutlined,
} from '@ant-design/icons';
import type { ToolCall } from '../../types/claw';

const { Panel } = Collapse;
const { Text, Paragraph } = Typography;

interface ToolCallCardProps {
  toolCall: ToolCall;
}

const ToolCallCard: React.FC<ToolCallCardProps> = ({ toolCall }) => {
  const getStatusIcon = () => {
    switch (toolCall.status) {
      case 'running':
        return <LoadingOutlined style={{ color: '#1890ff' }} />;
      case 'success':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'failed':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      default:
        return <ToolOutlined />;
    }
  };

  const getStatusColor = () => {
    switch (toolCall.status) {
      case 'running':
        return '#e6f7ff';
      case 'success':
        return '#f6ffed';
      case 'failed':
        return '#fff2f0';
      default:
        return '#fafafa';
    }
  };

  const getStatusTag = () => {
    switch (toolCall.status) {
      case 'running':
        return <Tag color="processing">运行中</Tag>;
      case 'success':
        return <Tag color="success">成功</Tag>;
      case 'failed':
        return <Tag color="error">失败</Tag>;
      default:
        return <Tag>未知</Tag>;
    }
  };

  return (
    <Card
      size="small"
      style={{
        marginTop: 8,
        marginBottom: 8,
        backgroundColor: getStatusColor(),
        borderLeft: `3px solid ${toolCall.status === 'success' ? '#52c41a' : toolCall.status === 'failed' ? '#ff4d4f' : '#1890ff'}`
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        {getStatusIcon()}
        <Text strong>{toolCall.toolName}</Text>
        {getStatusTag()}
        {toolCall.duration && (
          <Text type="secondary" style={{ fontSize: 12 }}>
            {toolCall.duration.toFixed(2)}s
          </Text>
        )}
      </div>

      <Collapse ghost>
        <Panel header="查看详情" key="1">
          <div style={{ marginBottom: 12 }}>
            <Text strong>输入参数：</Text>
            <Paragraph
              code
              style={{
                marginTop: 4,
                padding: 8,
                backgroundColor: '#f5f5f5',
                borderRadius: 4,
                fontSize: 12
              }}
            >
              {JSON.stringify(toolCall.input, null, 2)}
            </Paragraph>
          </div>

          {toolCall.output && (
            <div style={{ marginBottom: 12 }}>
              <Text strong>输出结果：</Text>
              <Paragraph
                code
                style={{
                  marginTop: 4,
                  padding: 8,
                  backgroundColor: '#f5f5f5',
                  borderRadius: 4,
                  fontSize: 12
                }}
              >
                {JSON.stringify(toolCall.output, null, 2)}
              </Paragraph>
            </div>
          )}

          {toolCall.error && (
            <div>
              <Text strong type="danger">错误信息：</Text>
              <Paragraph
                type="danger"
                style={{
                  marginTop: 4,
                  padding: 8,
                  backgroundColor: '#fff2f0',
                  borderRadius: 4,
                  fontSize: 12
                }}
              >
                {toolCall.error}
              </Paragraph>
            </div>
          )}
        </Panel>
      </Collapse>
    </Card>
  );
};

export default ToolCallCard;
