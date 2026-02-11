import React from 'react';
import { Card, Descriptions, Spin } from 'antd';
import { FileText, FileImage, Clock } from 'lucide-react';

interface FilePreviewProps {
  file: File | null;
  loading: boolean;
}

const FilePreview: React.FC<FilePreviewProps> = ({ file, loading }) => {
  const getFileIcon = (fileName: string) => {
    const extension = fileName.split('.').pop()?.toLowerCase();
    switch (extension) {
      case 'pdf':
        return <FileText size={24} className="text-red-500" />;
      case 'doc':
      case 'docx':
        return <FileText size={24} className="text-blue-500" />;
      case 'ppt':
      case 'pptx':
        return <FileText size={24} className="text-orange-500" />;
      case 'jpg':
      case 'jpeg':
      case 'png':
      case 'gif':
        return <FileText size={24} className="text-green-500" />;
      default:
        return <FileText size={24} className="text-gray-500" />;
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  if (loading) {
    return (
      <Card
        title="文件预览"
        style={{ borderRadius: 8, height: '100%' }}
        extra={<Clock size={16} className="text-blue-500" />}
      >
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 200 }}>
          <Spin size="large" description="加载中..." />
        </div>
      </Card>
    );
  }

  if (!file) {
    return (
      <Card
        title="文件预览"
        style={{ borderRadius: 8, height: '100%' }}
      >
        <div style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center', 
          height: 200,
          backgroundColor: '#f5f5f5',
          borderRadius: 8
        }}>
          <FileText size={48} className="text-gray-300" />
        </div>
        <div style={{ 
          textAlign: 'center', 
          marginTop: 16,
          color: '#999'
        }}>
          请上传文件以查看预览
        </div>
      </Card>
    );
  }

  return (
    <Card
      title="文件预览"
      style={{ borderRadius: 8, height: '100%' }}
      extra={getFileIcon(file.name)}
    >
      <Descriptions bordered size="small" style={{ marginBottom: 16 }}>
        <Descriptions.Item label="文件名">{file.name}</Descriptions.Item>
        <Descriptions.Item label="文件大小">{formatFileSize(file.size)}</Descriptions.Item>
        <Descriptions.Item label="文件类型">{file.type || '未知'}</Descriptions.Item>
        <Descriptions.Item label="最后修改">{new Date(file.lastModified).toLocaleString()}</Descriptions.Item>
      </Descriptions>
      <div style={{ 
        backgroundColor: '#f5f5f5',
        borderRadius: 8,
        padding: 16,
        textAlign: 'center'
      }}>
        {getFileIcon(file.name)}
        <div style={{ marginTop: 8 }}>
          {file.name}
        </div>
      </div>
    </Card>
  );
};

export default FilePreview;
