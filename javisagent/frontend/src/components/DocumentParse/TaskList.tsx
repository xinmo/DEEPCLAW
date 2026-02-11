import React, { useState } from 'react';
import { Button, Card, Tag, Space, message } from 'antd';
import { Plus, FileText, Clock, CheckCircle, X } from 'lucide-react';

interface Task {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  createdAt: string;
}

interface TaskListProps {
  hasNewFile?: boolean;
  hasNewUrl?: boolean;
}

const TaskList: React.FC<TaskListProps> = ({ hasNewFile = false, hasNewUrl = false }) => {
  const [tasks, setTasks] = useState<Task[]>([
    {
      id: '1',
      name: 'example.pdf',
      status: 'completed',
      createdAt: '2026-02-11 10:00:00'
    },
    {
      id: '2',
      name: 'demo.docx',
      status: 'running',
      createdAt: '2026-02-11 09:30:00'
    }
  ]);

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

  const handleNewTask = () => {
    // 检查是否有新上传的文件或链接
    if (!hasNewFile && !hasNewUrl) {
      message.warning('请先上传文件或输入网页链接');
      return;
    }
    
    const newTask: Task = {
      id: `${tasks.length + 1}`,
      name: hasNewFile ? '文件解析任务' : '网页解析任务',
      status: 'pending',
      createdAt: new Date().toLocaleString()
    };
    setTasks([newTask, ...tasks]);
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ margin: 0 }}>任务列表</h3>
        <Button type="primary" icon={<Plus size={16} />} onClick={handleNewTask}>
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
              marginBottom: 12
            }}
            hoverable
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
            <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
              创建时间: {task.createdAt}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default TaskList;
