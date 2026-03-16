import React, { useState } from 'react';
import { Upload, Button, Tabs, Card, Input, message } from 'antd';
import { UploadIcon, Link2, CloudUpload } from 'lucide-react';

const { TextArea } = Input;

interface FileUploadProps {
  onFileUpload: (file: File) => void;
  onUrlSubmit: (url: string) => void;
}

const FileUpload: React.FC<FileUploadProps> = ({ onFileUpload, onUrlSubmit }) => {
  const [activeTab, setActiveTab] = useState<string>('file');
  const [url, setUrl] = useState<string>('');

  const handleUrlSubmit = () => {
    if (!url.trim()) {
      message.error('请输入网页链接');
      return;
    }
    onUrlSubmit(url);
    message.success('网页链接提交成功');
    setUrl('');
  };

  const uploadProps = {
    name: 'file',
    multiple: false,
    showUploadList: false,
    beforeUpload: (file: File) => {
      onFileUpload(file);
      return false; // 阻止 Ant Design 自动上传
    },
  };

  const tabItems = [
    {
      key: 'file',
      label: (
        <>
          <UploadIcon /> 上传文件
        </>
      ),
      children: (
        <Upload.Dragger {...uploadProps} style={{ borderRadius: 8 }}>
          <p className="ant-upload-drag-icon">
            <UploadIcon size={32} />
          </p>
          <p className="ant-upload-text">点击或拖拽文件到此处上传</p>
          <p className="ant-upload-hint">
            支持 PDF、DOC、DOCX、PPT、PPTX、PNG、JPG 等格式，单个文件不超过 200MB
          </p>
        </Upload.Dragger>
      )
    },
    {
      key: 'url',
      label: (
        <>
          <Link2 /> 网页链接
        </>
      ),
      children: (
        <>
          <TextArea
            rows={4}
            placeholder="请输入网页链接"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            style={{ marginBottom: 16, borderRadius: 8 }}
          />
          <Button type="primary" onClick={handleUrlSubmit}>
            提交解析
          </Button>
        </>
      )
    }
  ];

  return (
    <Card
      style={{ 
        borderRadius: 12, 
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08)',
        textAlign: 'center',
        padding: '32px'
      }}
    >
      <div style={{ marginBottom: 24 }}>
        <CloudUpload size={48} className="text-blue-500" />
        <h3 style={{ margin: '16px 0 8px 0' }}>智能解析</h3>
        <p style={{ margin: 0, color: '#666' }}>让文档和网页内容为AI所用</p>
      </div>

      <Tabs activeKey={activeTab} onChange={setActiveTab} style={{ marginBottom: 24 }} items={tabItems} />

      <div style={{ marginTop: 32 }}>
        <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 16, textAlign: 'left' }}>示例</div>
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          {[
            { name: '网页解析', desc: '大模型RAG应用开发之PDF解析工具对比' },
            { name: '医学论文', desc: '医学临床研究论文' },
            { name: '学术报告', desc: '证券研究报告' }
          ].map((item, index) => (
            <Card key={index} size="small" style={{ width: 200, borderRadius: 8 }} hoverable>
              <div style={{ fontSize: 12, color: '#1890ff', marginBottom: 8 }}>{item.name}</div>
              <div style={{ fontSize: 12, color: '#666', lineHeight: 1.4 }}>{item.desc}</div>
            </Card>
          ))}
        </div>
      </div>
    </Card>
  );
};

export default FileUpload;
