import React from 'react';
import { Card, List, Tag, Typography } from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import type { PlanningTask } from '../../types/claw';

const { Text } = Typography;

interface PlanningCardProps {
  tasks: PlanningTask[];
}

const PlanningCard: React.FC<PlanningCardProps> = ({ tasks }) => {
  const getTaskIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'in_progress':
        return <SyncOutlined spin style={{ color: '#1890ff' }} />;
      case 'pending':
        return <ClockCircleOutlined style={{ color: '#d9d9d9' }} />;
      default:
        return <ClockCircleOutlined />;
    }
  };

  const getTaskTag = (status: string) => {
    switch (status) {
      case 'completed':
        return <Tag color="success">已完成</Tag>;
      case 'in_progress':
        return <Tag color="processing">进行中</Tag>;
      case 'pending':
        return <Tag color="default">待办</Tag>;
      default:
        return <Tag>未知</Tag>;
    }
  };

  return (
    <Card
      size="small"
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Text strong>📝 规划任务</Text>
          <Tag color="orange">{tasks.length} 项</Tag>
        </div>
      }
      style={{
        marginTop: 8,
        marginBottom: 8,
        backgroundColor: '#fffbf0',
        borderLeft: '3px solid #fa8c16'
      }}
    >
      <List
        size="small"
        dataSource={tasks}
        renderItem={(task) => (
          <List.Item
            style={{
              padding: '8px 0',
              borderBottom: '1px solid #f0f0f0'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, width: '100%' }}>
              {getTaskIcon(task.status)}
              <Text
                style={{
                  flex: 1,
                  textDecoration: task.status === 'completed' ? 'line-through' : 'none',
                  color: task.status === 'completed' ? '#999' : 'inherit'
                }}
              >
                {task.content}
              </Text>
              {getTaskTag(task.status)}
            </div>
          </List.Item>
        )}
      />
    </Card>
  );
};

export default PlanningCard;
