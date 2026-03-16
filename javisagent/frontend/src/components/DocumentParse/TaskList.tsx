import React from 'react';
import { Button, Card, Tag, Space, Popconfirm } from 'antd';
import { Plus, FileText, Clock, CheckCircle, X, Trash2 } from 'lucide-react';

export interface Task {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  createdAt: string;
  file?: File;
  result?: string;
  fileId?: string;
  fileName?: string;
  isUrlTask?: boolean;
}

interface TaskListProps {
  tasks: Task[];
  selectedTaskId?: string;
  onNewTask: () => void;
  onSelectTask: (taskId: string) => void;
  onDeleteTask: (taskId: string) => void;
}

const TaskList: React.FC<TaskListProps> = ({ tasks, selectedTaskId, onNewTask, onSelectTask, onDeleteTask }) => {
  const getStatusIcon = (status: Task['status']) => {
    switch (status) {
      case 'pending':
        return <Clock size={16} className="text-gray-400" />;
      case 'running':
        return <Clock size={16} className="text-blue-500" />;
      case 'completed':
        return <CheckCircle size={16} className="text-green-500" />;
      case 'failed':
        return <X size={16} className="text-red-500" />;
      default:
        return null;
    }
  };

  const getStatusTag = (status: Task['status']) => {
    switch (status) {
      case 'pending':
        return <Tag color="default">排队中</Tag>;
      case 'running':
        return <Tag color="blue">解析中</Tag>;
      case 'completed':
        return <Tag color="green">已完成</Tag>;
      case 'failed':
        return <Tag color="red">失败</Tag>;
      default:
        return null;
    }
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ margin: 0 }}>任务列表</h3>
        <Button type="primary" icon={<Plus size={16} />} onClick={onNewTask}>
          新建任务
        </Button>
      </div>
      <div style={{ flex: 1, overflow: 'auto' }}>
        {tasks.map((task) => (
          <Card
            key={task.id}
            size="small"
            style={{
              width: '100%',
              borderRadius: 8,
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
              marginBottom: 12,
              border: selectedTaskId === task.id ? '2px solid #1890ff' : undefined,
              cursor: 'pointer'
            }}
            hoverable
            onClick={() => onSelectTask(task.id)}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Space size={8}>
                <FileText size={16} />
                <span style={{ fontWeight: 500 }}>{task.name}</span>
              </Space>
              <Space size={8}>
                {getStatusIcon(task.status)}
                {getStatusTag(task.status)}
              </Space>
            </div>
            <div style={{ marginTop: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 12, color: '#666' }}>创建时间: {task.createdAt}</span>
              <Popconfirm
                title="确定删除该任务？"
                onConfirm={() => onDeleteTask(task.id)}
                okText="删除"
                cancelText="取消"
              >
                <Button type="text" size="small" danger icon={<Trash2 size={14} />} />
              </Popconfirm>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default TaskList;
