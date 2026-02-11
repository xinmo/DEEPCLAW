import React, { useState, useEffect } from 'react';
import { Row, Col, message } from 'antd';
import TaskList from '../components/DocumentParse/TaskList';
import FileUpload from '../components/DocumentParse/FileUpload';
import FilePreview from '../components/DocumentParse/FilePreview';
import MarkdownViewer from '../components/DocumentParse/MarkdownViewer';
import api from '../services/api';

interface ExtractProgress {
  extracted_pages: number;
  total_pages: number;
}

const DocumentParsePage: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [url, setUrl] = useState<string>('');
  const [markdown, setMarkdown] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [currentTaskId, setCurrentTaskId] = useState<string>('');
  const [hasNewFile, setHasNewFile] = useState<boolean>(false);
  const [hasNewUrl, setHasNewUrl] = useState<boolean>(false);
  const [progress, setProgress] = useState<ExtractProgress | undefined>(undefined);

  useEffect(() => {
    let intervalId: NodeJS.Timeout | null = null;

    if (currentTaskId && loading) {
      intervalId = setInterval(async () => {
        try {
          const response = await api.getTaskStatus(currentTaskId);
          // 更新进度信息
          if (response.progress) {
            setProgress(response.progress);
          }
          if (response.task.status === 'completed') {
            setMarkdown(response.result || '解析完成，但没有返回结果');
            setLoading(false);
            setProgress(undefined);
            if (intervalId) clearInterval(intervalId);
          } else if (response.task.status === 'failed') {
            message.error('解析失败');
            setLoading(false);
            setProgress(undefined);
            if (intervalId) clearInterval(intervalId);
          }
        } catch (error) {
          console.error('查询任务状态失败:', error);
        }
      }, 2000);
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [currentTaskId, loading]);

  const handleFileUpload = async (uploadedFile: File) => {
    try {
      setFile(uploadedFile);
      setHasNewFile(true);
      setHasNewUrl(false);
      setLoading(true);
      setMarkdown('');
      setProgress(undefined);

      const uploadResponse = await api.uploadFile(uploadedFile);
      const parseResponse = await api.parseDocument(uploadResponse.file_id);
      setCurrentTaskId(parseResponse.task_id);
      message.success('文件上传成功，正在解析...');
    } catch (error: any) {
      console.error('上传文件失败:', error);
      message.error(error.response?.data?.detail || '上传文件失败');
      setLoading(false);
      setProgress(undefined);
    }
  };

  const handleUrlSubmit = async (submittedUrl: string) => {
    try {
      setFile(null);
      setUrl(submittedUrl);
      setHasNewFile(false);
      setHasNewUrl(true);
      setLoading(true);
      setMarkdown('');
      setProgress(undefined);

      const parseResponse = await api.parseUrl(submittedUrl);
      setCurrentTaskId(parseResponse.task_id);
      message.success('网页链接提交成功，正在解析...');
    } catch (error: any) {
      console.error('提交网页链接失败:', error);
      message.error(error.response?.data?.detail || '提交网页链接失败');
      setLoading(false);
      setProgress(undefined);
    }
  };

  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <TaskList hasNewFile={hasNewFile} hasNewUrl={hasNewUrl} />
        </Col>
        <Col span={18}>
          <FileUpload onFileUpload={handleFileUpload} onUrlSubmit={handleUrlSubmit} />
        </Col>
      </Row>
      
      {(file || markdown) && (
        <Row gutter={[16, 16]}>
          <Col span={12}>
            <FilePreview file={file} loading={loading} />
          </Col>
          <Col span={12}>
            <MarkdownViewer markdown={markdown} loading={loading} progress={progress} />
          </Col>
        </Row>
      )}
    </div>
  );
};

export default DocumentParsePage;
