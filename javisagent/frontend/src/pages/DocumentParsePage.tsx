import React, { useState, useEffect, useRef } from 'react';
import { Row, Col, message } from 'antd';
import TaskList, { type Task } from '../components/DocumentParse/TaskList';
import FileUpload from '../components/DocumentParse/FileUpload';
import FilePreview from '../components/DocumentParse/FilePreview';
import MarkdownViewer from '../components/DocumentParse/MarkdownViewer';
import api from '../services/api';

interface ExtractProgress {
  extracted_pages: number;
  total_pages: number;
}

interface TaskProgress {
  [taskId: string]: ExtractProgress | undefined;
}

const DocumentParsePage: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string>('');
  const [taskProgress, setTaskProgress] = useState<TaskProgress>({});
  const [_loading, setLoading] = useState<boolean>(true);
  const pollingIntervalsRef = useRef<Map<string, ReturnType<typeof setInterval>>>(new Map());

  // 获取当前选中的任务
  const selectedTask = tasks.find(t => t.id === selectedTaskId);

  /**
   * 加载历史任务列表
   */
  useEffect(() => {
    const loadTasks = async () => {
      try {
        const response = await api.getTasks();
        const loadedTasks: Task[] = response.map(task => ({
          id: task.id,
          name: task.name,
          status: task.status,
          createdAt: new Date(task.created_at).toLocaleString(),
          result: task.result || undefined,
          fileId: task.file_id || undefined,
          fileName: task.file_name || undefined,
          isUrlTask: !task.file_id && task.name.startsWith('http')
        }));
        setTasks(loadedTasks);

        // 恢复 running 状态任务的轮询
        loadedTasks.forEach(task => {
          if (task.status === 'running') {
            startPolling(task.id, task.id);
          }
        });
      } catch (error) {
        console.error('加载任务列表失败:', error);
      } finally {
        setLoading(false);
      }
    };
    loadTasks();
  }, []);

  // 清理轮询
  useEffect(() => {
    return () => {
      pollingIntervalsRef.current.forEach(interval => clearInterval(interval));
    };
  }, []);

  // 开始轮询任务状态
  const startPolling = (taskId: string, apiTaskId: string) => {
    // 如果已经在轮询，不重复启动
    if (pollingIntervalsRef.current.has(taskId)) return;

    const intervalId = setInterval(async () => {
      try {
        const response = await api.getTaskStatus(apiTaskId);

        // 更新进度
        if (response.progress) {
          setTaskProgress(prev => ({ ...prev, [taskId]: response.progress }));
        }

        if (response.task.status === 'completed') {
          // 更新任务状态和结果
          setTasks(prev => prev.map(t =>
            t.id === taskId ? { ...t, status: 'completed', result: response.result || '解析完成，但没有返回结果' } : t
          ));
          setTaskProgress(prev => ({ ...prev, [taskId]: undefined }));
          stopPolling(taskId);
          message.success('解析完成');
        } else if (response.task.status === 'failed') {
          setTasks(prev => prev.map(t =>
            t.id === taskId ? { ...t, status: 'failed' } : t
          ));
          setTaskProgress(prev => ({ ...prev, [taskId]: undefined }));
          stopPolling(taskId);
          message.error('解析失败');
        }
      } catch (error) {
        console.error('查询任务状态失败:', error);
      }
    }, 2000);

    pollingIntervalsRef.current.set(taskId, intervalId);
  };

  // 停止轮询
  const stopPolling = (taskId: string) => {
    const interval = pollingIntervalsRef.current.get(taskId);
    if (interval) {
      clearInterval(interval);
      pollingIntervalsRef.current.delete(taskId);
    }
  };

  const handleFileUpload = async (uploadedFile: File) => {
    const taskId = Date.now().toString();

    // 立即创建任务并选中，显示文件预览
    const newTask: Task = {
      id: taskId,
      name: uploadedFile.name,
      status: 'running',
      createdAt: new Date().toLocaleString(),
      file: uploadedFile
    };
    setTasks(prev => [newTask, ...prev]);
    setSelectedTaskId(taskId);

    try {
      const uploadResponse = await api.uploadFile(uploadedFile);
      const parseResponse = await api.parseDocument(uploadResponse.file_id, uploadResponse.file_name);

      // 开始轮询
      startPolling(taskId, parseResponse.task_id);
      message.success('文件上传成功，正在解析...');
    } catch (error: any) {
      console.error('上传文件失败:', error);
      message.error(error.response?.data?.detail || '上传文件失败');
      setTasks(prev => prev.map(t =>
        t.id === taskId ? { ...t, status: 'failed' } : t
      ));
    }
  };

  const handleUrlSubmit = async (submittedUrl: string) => {
    const taskId = Date.now().toString();

    const newTask: Task = {
      id: taskId,
      name: submittedUrl,
      status: 'running',
      createdAt: new Date().toLocaleString()
    };
    setTasks(prev => [newTask, ...prev]);
    setSelectedTaskId(taskId);

    try {
      const parseResponse = await api.parseUrl(submittedUrl);
      startPolling(taskId, parseResponse.task_id);
      message.success('网页链接提交成功，正在解析...');
    } catch (error: any) {
      console.error('提交网页链接失败:', error);
      message.error(error.response?.data?.detail || '提交网页链接失败');
      setTasks(prev => prev.map(t =>
        t.id === taskId ? { ...t, status: 'failed' } : t
      ));
    }
  };

  const handleNewTask = () => {
    setSelectedTaskId('');
  };

  const handleSelectTask = (taskId: string) => {
    setSelectedTaskId(taskId);
  };

  const handleDeleteTask = async (taskId: string) => {
    try {
      // 先调用后端 API 删除任务
      await api.deleteTask(taskId);
      
      stopPolling(taskId);
      setTasks(prev => prev.filter(t => t.id !== taskId));
      setTaskProgress(prev => {
        const newProgress = { ...prev };
        delete newProgress[taskId];
        return newProgress;
      });

      if (selectedTaskId === taskId) {
        setSelectedTaskId('');
      }
      message.success('任务已删除');
    } catch (error: any) {
      message.error(error.response?.data?.detail || '删除任务失败');
    }
  };

  const hasSelectedTask = !!selectedTask;
  const isLoading = selectedTask?.status === 'running';
  const currentProgress = selectedTask ? taskProgress[selectedTask.id] : undefined;

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col span={4}>
          <TaskList
            tasks={tasks}
            selectedTaskId={selectedTaskId}
            onNewTask={handleNewTask}
            onSelectTask={handleSelectTask}
            onDeleteTask={handleDeleteTask}
          />
        </Col>
        <Col span={20}>
          {!hasSelectedTask ? (
            <FileUpload onFileUpload={handleFileUpload} onUrlSubmit={handleUrlSubmit} />
          ) : (
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <FilePreview 
                  file={selectedTask.file || null} 
                  loading={false} 
                  fileId={selectedTask.fileId}
                  fileName={selectedTask.fileName}
                  isUrlTask={selectedTask.isUrlTask}
                />
              </Col>
              <Col span={12}>
                <MarkdownViewer
                  markdown={selectedTask.result || ''}
                  loading={isLoading}
                  progress={currentProgress}
                />
              </Col>
            </Row>
          )}
        </Col>
      </Row>
    </div>
  );
};

export default DocumentParsePage;
