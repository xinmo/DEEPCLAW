import React from 'react';
import { Card, Progress, Tag, Typography, Space } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  RobotOutlined,
} from '@ant-design/icons';
import type { SubAgent } from '../../types/claw';

const { Text, Paragraph } = Typography;

interface SubAgentCardProps {
  subAgent: SubAgent;
}

const SubAgentCard: React.FC<SubAgentCardProps> = ({ subAgent }) => {
  const getStatusIcon = () => {
    switch (subAgent.status) {
      case 'running':
        return <LoadingOutlined style={{ color: '#722ed1' }} />;
      case 'success':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'failed':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      default:
        return <RobotOutlined />;
    }
  };

  const getStatusColor = () => {
    switch (subAgent.status) {
      case 'running':
        return '#f9f0ff';
      case 'success':
        return '#f6ffed';
      case 'failed':
        return '#fff2f0';
      default:
        return '#fafafa';
    }
  };

  const getStatusTag = () => {
    switch (subAgent.status) {
      case 'running':
        return <Tag color="purple">运行中</Tag>;
      case 'success':
        return <Tag color="success">已完成</Tag>;
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
        borderLeft: `3px solid ${subAgent.status === 'success' ? '#52c41a' : subAgent.status === 'failed' ? '#ff4d4f' : '#722ed1'}`
      }}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="small">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {getStatusIcon()}
          <Text strong>{subAgent.name}</Text>
          {getStatusTag()}
          {subAgent.duration && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {subAgent.duration.toFixed(2)}s
            </Text>
          )}
        </div>

        <div>
          <Text type="secondary" style={{ fontSize: 12 }}>任务：</Text>
          <Paragraph style={{ marginBottom: 0, marginTop: 4 }}>
            {subAgent.task}
          </Paragraph>
        </div>

        {subAgent.status === 'running' && subAgent.progress !== undefined && (
          <Progress
            percent={subAgent.progress}
            size="small"
            status="active"
            strokeColor="#722ed1"
          />
        )}

        {subAgent.result && (
          <div>
            <Text type="secondary" style={{ fontSize: 12 }}>结果：</Text>
            <Paragraph
              style={{
                marginTop: 4,
                padding: 8,
                backgroundColor: '#f5f5f5',
                borderRadius: 4,
                fontSize: 12,
                marginBottom: 0
              }}
            >
              {typeof subAgent.result === 'string'
                ? subAgent.result
                : JSON.stringify(subAgent.result, null, 2)}
            </Paragraph>
          </div>
        )}
      </Space>
    </Card>
  );
};

export default SubAgentCard;
