import React, { useEffect, useRef, useState } from 'react';
import { Card, Descriptions, Spin } from 'antd';
import { FileText, Image, Link } from 'lucide-react';

import api from '../../services/api';

interface FilePreviewProps {
  file: File | null;
  loading: boolean;
  fileId?: string;
  fileName?: string;
  isUrlTask?: boolean;
}

const cardStyle = {
  borderRadius: 8,
  height: 'calc(100vh - 180px)',
};

const centerBoxStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  justifyContent: 'center',
  alignItems: 'center',
  height: 'calc(100vh - 300px)',
  borderRadius: 8,
};

const previewAreaStyle: React.CSSProperties = {
  flex: 1,
  overflow: 'auto',
  display: 'flex',
  justifyContent: 'center',
  alignItems: 'flex-start',
};

const textPreviewStyle: React.CSSProperties = {
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
  width: '100%',
};

const docxContainerStyle: React.CSSProperties = {
  backgroundColor: '#fff',
  padding: 16,
};

function getExtension(name: string): string {
  return name.split('.').pop()?.toLowerCase() || '';
}

function getFileIcon(fileName: string) {
  const ext = getExtension(fileName);
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
    case 'webp':
    case 'bmp':
      return <Image size={24} style={{ color: '#52c41a' }} />;
    default:
      return <FileText size={24} style={{ color: '#8c8c8c' }} />;
  }
}

function formatFileSize(bytes: number) {
  if (bytes === 0) {
    return '0 Bytes';
  }
  const units = ['Bytes', 'KB', 'MB', 'GB'];
  const index = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${parseFloat((bytes / 1024 ** index).toFixed(2))} ${units[index]}`;
}

const FilePreview: React.FC<FilePreviewProps> = ({ file, loading, fileId, fileName, isUrlTask }) => {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [textContent, setTextContent] = useState<string | null>(null);
  const [docxLoading, setDocxLoading] = useState(false);
  const [docxRendered, setDocxRendered] = useState(false);
  const [remoteFileLoading, setRemoteFileLoading] = useState(false);
  const [remoteFile, setRemoteFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const docxContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!fileId || file) {
      setRemoteFile(null);
      setError(null);
      return;
    }

    let cancelled = false;
    setRemoteFileLoading(true);
    setError(null);

    void api
      .getFile(fileId)
      .then((blob) => {
        if (cancelled) {
          return;
        }
        const nextFileName = fileName || `file_${fileId}`;
        setRemoteFile(new File([blob], nextFileName, { type: blob.type }));
      })
      .catch((fetchError) => {
        console.error('Failed to load remote file preview.', fetchError);
        if (!cancelled) {
          setError('文件加载失败，请稍后重试。');
        }
      })
      .finally(() => {
        if (!cancelled) {
          setRemoteFileLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [file, fileId, fileName]);

  const currentFile = file || remoteFile;

  useEffect(() => {
    if (!currentFile) {
      setPreviewUrl(null);
      setTextContent(null);
      setDocxRendered(false);
      return;
    }

    const url = URL.createObjectURL(currentFile);
    setPreviewUrl(url);
    setDocxRendered(false);

    const ext = getExtension(currentFile.name);
    if (['txt', 'md', 'json', 'html'].includes(ext)) {
      const reader = new FileReader();
      reader.onload = (event) => {
        setTextContent((event.target?.result as string) || '');
      };
      reader.readAsText(currentFile);
    } else {
      setTextContent(null);
    }

    return () => {
      URL.revokeObjectURL(url);
    };
  }, [currentFile]);

  useEffect(() => {
    if (!currentFile || docxRendered || getExtension(currentFile.name) !== 'docx') {
      return;
    }

    let cancelled = false;
    const timer = window.setTimeout(() => {
      if (!docxContainerRef.current) {
        return;
      }

      setDocxLoading(true);
      docxContainerRef.current.innerHTML = '';

      void (async () => {
        try {
          const { renderAsync } = await import('docx-preview');
          if (cancelled || !docxContainerRef.current) {
            return;
          }
          await renderAsync(currentFile, docxContainerRef.current, undefined, {
            className: 'docx-preview',
            inWrapper: true,
            ignoreWidth: false,
            ignoreHeight: false,
            ignoreFonts: false,
            breakPages: true,
            useBase64URL: true,
          });
          if (!cancelled) {
            setDocxRendered(true);
          }
        } catch (renderError) {
          console.error('Failed to render DOCX preview.', renderError);
          if (!cancelled) {
            setError('DOCX 预览加载失败。');
          }
        } finally {
          if (!cancelled) {
            setDocxLoading(false);
          }
        }
      })();
    }, 100);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [currentFile, docxRendered]);

  const renderPreview = () => {
    if (!currentFile || !previewUrl) {
      return null;
    }

    const ext = getExtension(currentFile.name);

    if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'].includes(ext)) {
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

    if (ext === 'docx') {
      return (
        <div style={{ width: '100%', height: 'calc(100vh - 350px)', overflow: 'auto' }}>
          {docxLoading ? (
            <div style={{ ...centerBoxStyle, height: '100%' }}>
              <Spin size="large" tip="正在加载 DOCX 预览..." />
            </div>
          ) : null}
          <div
            ref={docxContainerRef}
            style={{
              ...docxContainerStyle,
              display: docxLoading ? 'none' : 'block',
            }}
          />
        </div>
      );
    }

    if (ext === 'doc') {
      return (
        <div style={{ ...centerBoxStyle, backgroundColor: '#fafafa' }}>
          {getFileIcon(currentFile.name)}
          <div style={{ marginTop: 16, color: '#666' }}>
            `.doc` 暂不支持在线预览，请转换为 `.docx` 后再查看。
          </div>
        </div>
      );
    }

    if (textContent !== null) {
      return <pre style={textPreviewStyle}>{textContent}</pre>;
    }

    return (
      <div style={{ ...centerBoxStyle, backgroundColor: '#fafafa' }}>
        {getFileIcon(currentFile.name)}
        <div style={{ marginTop: 16, color: '#666' }}>当前文件类型暂不支持预览。</div>
      </div>
    );
  };

  if (isUrlTask) {
    return (
      <Card title="文件预览" style={cardStyle}>
        <div style={{ ...centerBoxStyle, backgroundColor: '#fafafa' }}>
          <Link size={64} style={{ color: '#1890ff' }} />
          <div style={{ marginTop: 16, color: '#666' }}>当前任务为 URL 解析，没有本地文件预览。</div>
        </div>
      </Card>
    );
  }

  if (remoteFileLoading) {
    return (
      <Card title="文件预览" style={cardStyle}>
        <div style={centerBoxStyle}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: '#999' }}>正在加载文件...</div>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card title="文件预览" style={cardStyle}>
        <div style={{ ...centerBoxStyle, backgroundColor: '#fff2f0' }}>
          <FileText size={64} style={{ color: '#ff4d4f' }} />
          <div style={{ marginTop: 16, color: '#ff4d4f' }}>{error}</div>
        </div>
      </Card>
    );
  }

  if (!currentFile) {
    return (
      <Card title="文件预览" style={cardStyle}>
        <div style={{ ...centerBoxStyle, backgroundColor: '#fafafa' }}>
          <FileText size={64} style={{ color: '#d9d9d9' }} />
          <div style={{ marginTop: 16, color: '#999' }}>请上传文件后查看预览。</div>
        </div>
      </Card>
    );
  }

  return (
    <Card
      title="文件预览"
      style={{ ...cardStyle, display: 'flex', flexDirection: 'column' }}
      extra={getFileIcon(currentFile.name)}
      styles={{ body: { flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column' } }}
    >
      <Descriptions bordered size="small" column={2} style={{ marginBottom: 16 }}>
        <Descriptions.Item label="文件名">{currentFile.name}</Descriptions.Item>
        <Descriptions.Item label="大小">{formatFileSize(currentFile.size)}</Descriptions.Item>
      </Descriptions>
      <div style={previewAreaStyle}>{loading ? <Spin size="large" /> : renderPreview()}</div>
    </Card>
  );
};

export default FilePreview;
