import React, { useState, useEffect, useRef } from 'react';
import { Card, Descriptions, Spin } from 'antd';
import { FileText, Image, Link } from 'lucide-react';
import { renderAsync } from 'docx-preview';
import api from '../../services/api';

interface FilePreviewProps {
  file: File | null;
  loading: boolean;
  fileId?: string;
  fileName?: string;
  isUrlTask?: boolean;
}

const FilePreview: React.FC<FilePreviewProps> = ({ file, loading, fileId, fileName, isUrlTask }) => {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [textContent, setTextContent] = useState<string | null>(null);
  const [docxLoading, setDocxLoading] = useState<boolean>(false);
  const [docxRendered, setDocxRendered] = useState<boolean>(false);
  const [remoteFileLoading, setRemoteFileLoading] = useState<boolean>(false);
  const [remoteFile, setRemoteFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const docxContainerRef = useRef<HTMLDivElement>(null);

  /**
   * 从远程加载文件
   */
  useEffect(() => {
    if (fileId && !file) {
      setRemoteFileLoading(true);
      setError(null);
      
      api.getFile(fileId)
        .then(blob => {
          const remoteFileName = fileName || `file_${fileId}`;
          const remoteFileObj = new File([blob], remoteFileName, { type: blob.type });
          setRemoteFile(remoteFileObj);
        })
        .catch(err => {
          console.error('加载远程文件失败:', err);
          setError('文件加载失败，可能已被删除');
        })
        .finally(() => {
          setRemoteFileLoading(false);
        });
    } else {
      setRemoteFile(null);
      setError(null);
    }
  }, [fileId, fileName, file]);

  // 合并本地文件和远程文件
  const currentFile = file || remoteFile;

  // 处理文件 URL 和文本内容
  useEffect(() => {
    if (currentFile) {
      const url = URL.createObjectURL(currentFile);
      setPreviewUrl(url);
      setDocxRendered(false);

      const ext = currentFile.name.split('.').pop()?.toLowerCase();

      // 处理文本文件
      if (ext === 'txt' || ext === 'md' || ext === 'json' || ext === 'html') {
        const reader = new FileReader();
        reader.onload = (e) => {
          setTextContent(e.target?.result as string);
        };
        reader.readAsText(currentFile);
      } else {
        setTextContent(null);
      }

      return () => {
        URL.revokeObjectURL(url);
      };
    } else {
      setPreviewUrl(null);
      setTextContent(null);
      setDocxRendered(false);
    }
  }, [currentFile]);

  // 单独处理 Word 文档渲染（需要等待 ref 挂载）
  useEffect(() => {
    if (!currentFile || docxRendered) return;

    const ext = currentFile.name.split('.').pop()?.toLowerCase();
    if (ext !== 'docx') return;

    // 使用 setTimeout 确保 DOM 已渲染
    const timer = setTimeout(() => {
      if (!docxContainerRef.current) return;

      setDocxLoading(true);
      docxContainerRef.current.innerHTML = ''; // 清空之前的内容

      renderAsync(currentFile, docxContainerRef.current, undefined, {
        className: 'docx-preview',
        inWrapper: true,
        ignoreWidth: false,
        ignoreHeight: false,
        ignoreFonts: false,
        breakPages: true,
        useBase64URL: true,
      }).then(() => {
        setDocxLoading(false);
        setDocxRendered(true);
      }).catch((err) => {
        console.error('Word 文档预览失败:', err);
        setDocxLoading(false);
      });
    }, 100);

    return () => clearTimeout(timer);
  }, [currentFile, docxRendered]);

  const getFileIcon = (fileName: string) => {
    const ext = fileName.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'pdf':
        return <FileText size={24} style={{ color: '#ff4d4f' }} />;
      case 'doc':
      case 'docx':
        return <FileText size={24} style={{ color: '#1890ff' }} />;
      case 'jpg':
      case 'jpeg':
      case 'png':
      case 'gif':
        return <Image size={24} style={{ color: '#52c41a' }} />;
      default:
        return <FileText size={24} style={{ color: '#8c8c8c' }} />;
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const renderPreview = () => {
    if (!currentFile || !previewUrl) return null;
    const ext = currentFile.name.split('.').pop()?.toLowerCase();

    if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'].includes(ext || '')) {
      return (
        <img
          src={previewUrl}
          alt={currentFile.name}
          style={{ maxWidth: '100%', maxHeight: 'calc(100vh - 350px)', objectFit: 'contain' }}
        />
      );
    }

    if (ext === 'pdf') {
      return (
        <iframe
          src={previewUrl}
          title={currentFile.name}
          style={{ width: '100%', height: 'calc(100vh - 350px)', border: 'none' }}
        />
      );
    }

    // Word 文档预览
    if (ext === 'docx') {
      return (
        <div style={{ width: '100%', height: 'calc(100vh - 350px)', overflow: 'auto' }}>
          {docxLoading && (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
              <Spin size="large" />
            </div>
          )}
          <div
            ref={docxContainerRef}
            style={{
              display: docxLoading ? 'none' : 'block',
              backgroundColor: '#fff',
              padding: 16
            }}
          />
        </div>
      );
    }

    // .doc 格式提示
    if (ext === 'doc') {
      return (
        <div style={{ textAlign: 'center', padding: 40 }}>
          {getFileIcon(currentFile.name)}
          <div style={{ marginTop: 16, color: '#666' }}>
            .doc 格式暂不支持预览，请转换为 .docx 格式
          </div>
        </div>
      );
    }

    if (textContent !== null) {
      return (
        <pre style={{
          maxHeight: 'calc(100vh - 350px)',
          overflow: 'auto',
          backgroundColor: '#f5f5f5',
          padding: 16,
          borderRadius: 8,
          fontSize: 13,
          lineHeight: 1.6,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          margin: 0,
          width: '100%'
        }}>
          {textContent}
        </pre>
      );
    }

    return (
      <div style={{ textAlign: 'center', padding: 40 }}>
        {getFileIcon(currentFile.name)}
        <div style={{ marginTop: 16, color: '#666' }}>该文件类型暂不支持预览</div>
      </div>
    );
  };

  // URL 解析任务无文件预览
  if (isUrlTask) {
    return (
      <Card title="文件预览" style={{ borderRadius: 8, height: 'calc(100vh - 180px)' }}>
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          height: 'calc(100vh - 300px)',
          backgroundColor: '#fafafa',
          borderRadius: 8
        }}>
          <Link size={64} style={{ color: '#1890ff' }} />
          <div style={{ marginTop: 16, color: '#666' }}>该任务为 URL 解析，无文件预览</div>
        </div>
      </Card>
    );
  }

  // 远程文件加载中
  if (remoteFileLoading) {
    return (
      <Card title="文件预览" style={{ borderRadius: 8, height: 'calc(100vh - 180px)' }}>
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          height: 'calc(100vh - 300px)',
        }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: '#999' }}>正在加载文件...</div>
        </div>
      </Card>
    );
  }

  // 文件加载失败
  if (error) {
    return (
      <Card title="文件预览" style={{ borderRadius: 8, height: 'calc(100vh - 180px)' }}>
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          height: 'calc(100vh - 300px)',
          backgroundColor: '#fff2f0',
          borderRadius: 8
        }}>
          <FileText size={64} style={{ color: '#ff4d4f' }} />
          <div style={{ marginTop: 16, color: '#ff4d4f' }}>{error}</div>
        </div>
      </Card>
    );
  }

  if (!currentFile) {
    return (
      <Card title="文件预览" style={{ borderRadius: 8, height: 'calc(100vh - 180px)' }}>
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          height: 'calc(100vh - 300px)',
          backgroundColor: '#fafafa',
          borderRadius: 8
        }}>
          <FileText size={64} style={{ color: '#d9d9d9' }} />
          <div style={{ marginTop: 16, color: '#999' }}>请上传文件以查看预览</div>
        </div>
      </Card>
    );
  }

  return (
    <Card
      title="文件预览"
      style={{ borderRadius: 8, height: 'calc(100vh - 180px)', display: 'flex', flexDirection: 'column' }}
      extra={getFileIcon(currentFile.name)}
      styles={{ body: { flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column' } }}
    >
      <Descriptions bordered size="small" column={2} style={{ marginBottom: 16 }}>
        <Descriptions.Item label="文件名">{currentFile.name}</Descriptions.Item>
        <Descriptions.Item label="大小">{formatFileSize(currentFile.size)}</Descriptions.Item>
      </Descriptions>
      <div style={{ flex: 1, overflow: 'auto', display: 'flex', justifyContent: 'center', alignItems: 'flex-start' }}>
        {loading ? <Spin size="large" /> : renderPreview()}
      </div>
    </Card>
  );
};

export default FilePreview;
