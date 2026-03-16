import React from 'react';
import { Card, Spin, Typography, Progress } from 'antd';
import ReactMarkdown from 'react-markdown';
import { Clock, FileText } from 'lucide-react';

const { Title, Text } = Typography;

interface ExtractProgress {
  extracted_pages: number;
  total_pages: number;
}

interface MarkdownViewerProps {
  markdown: string;
  loading: boolean;
  progress?: ExtractProgress;
}

const MarkdownViewer: React.FC<MarkdownViewerProps> = ({ markdown, loading, progress }) => {
  if (loading) {
    const percent = progress && progress.total_pages > 0
      ? Math.round((progress.extracted_pages / progress.total_pages) * 100)
      : 0;

    return (
      <Card
        title="解析结果"
        style={{ borderRadius: 8, height: 'calc(100vh - 180px)' }}
        extra={<Clock size={16} style={{ color: '#1890ff' }} />}
      >
        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', height: 'calc(100vh - 300px)' }}>
          {progress && progress.total_pages > 0 ? (
            <div style={{ width: '80%', maxWidth: 300, textAlign: 'center' }}>
              <Progress
                type="circle"
                percent={percent}
                format={() => (
                  <div>
                    <div style={{ fontSize: 24, fontWeight: 'bold', color: '#1890ff' }}>
                      {progress.extracted_pages}/{progress.total_pages}
                    </div>
                    <div style={{ fontSize: 12, color: '#999' }}>页</div>
                  </div>
                )}
              />
              <div style={{ marginTop: 16 }}>
                <Text type="secondary">正在解析文档...</Text>
              </div>
            </div>
          ) : (
            <>
              <Spin size="large" />
              <div style={{ marginTop: 16, textAlign: 'center' }}>
                <Text type="secondary">正在准备解析...</Text>
              </div>
            </>
          )}
        </div>
      </Card>
    );
  }

  if (!markdown) {
    return (
      <Card
        title="解析结果"
        style={{ borderRadius: 8, height: 'calc(100vh - 180px)' }}
      >
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
          <div style={{ marginTop: 16, color: '#999' }}>
            解析完成后将显示 Markdown 内容
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card
      title="解析结果"
      style={{ borderRadius: 8, height: 'calc(100vh - 180px)', display: 'flex', flexDirection: 'column' }}
      styles={{ body: { flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' } }}
    >
      <div
        style={{
          flex: 1,
          overflow: 'auto',
          padding: 16,
          backgroundColor: '#fafafa',
          borderRadius: 8
        }}
      >
        <ReactMarkdown
          components={{
            code: ({ className, children, ...props }) => {
              const match = /language-(\w+)/.exec(className || '');
              const isInline = !match;
              return !isInline ? (
                <pre style={{ padding: 12, backgroundColor: '#f0f0f0', borderRadius: 6, overflow: 'auto' }}>
                  <code className={className} {...props}>
                    {children}
                  </code>
                </pre>
              ) : (
                <code style={{ padding: '2px 4px', backgroundColor: '#f0f0f0', borderRadius: 3 }} {...props}>
                  {children}
                </code>
              );
            },
            img: ({ src, alt, title, ...props }) => (
              <div style={{ margin: '16px 0', textAlign: 'center' }}>
                <img 
                  src={src} 
                  alt={alt} 
                  title={title} 
                  style={{ 
                    maxWidth: '100%', 
                    maxHeight: 400, 
                    objectFit: 'contain',
                    borderRadius: 4,
                    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)'
                  }} 
                  {...props} 
                />
                {alt && (
                  <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>{alt}</div>
                )}
              </div>
            ),
            h1: ({ children, ...props }) => (
              <Title level={2} style={{ margin: '16px 0' }} {...props}>
                {children}
              </Title>
            ),
            h2: ({ children, ...props }) => (
              <Title level={3} style={{ margin: '16px 0' }} {...props}>
                {children}
              </Title>
            ),
            h3: ({ children, ...props }) => (
              <Title level={4} style={{ margin: '16px 0' }} {...props}>
                {children}
              </Title>
            ),
            p: ({ children, ...props }) => (
              <p style={{ margin: '8px 0', lineHeight: 1.6 }} {...props}>
                {children}
              </p>
            ),
            ul: ({ children, ...props }) => (
              <ul style={{ margin: '8px 0', paddingLeft: 24 }} {...props}>
                {children}
              </ul>
            ),
            ol: ({ children, ...props }) => (
              <ol style={{ margin: '8px 0', paddingLeft: 24 }} {...props}>
                {children}
              </ol>
            ),
            li: ({ children, ...props }) => (
              <li style={{ margin: '4px 0' }} {...props}>
                {children}
              </li>
            ),
            table: ({ children, ...props }) => (
              <div style={{ margin: '16px 0', overflow: 'auto' }} {...props}>
                <table style={{ width: '100%', borderCollapse: 'collapse', border: '1px solid #e8e8e8' }}>
                  {children}
                </table>
              </div>
            ),
            th: ({ children, ...props }) => (
              <th style={{ 
                padding: 8, 
                border: '1px solid #e8e8e8', 
                backgroundColor: '#fafafa',
                fontWeight: 'bold',
                textAlign: 'left'
              }} {...props}>
                {children}
              </th>
            ),
            td: ({ children, ...props }) => (
              <td style={{ 
                padding: 8, 
                border: '1px solid #e8e8e8',
                textAlign: 'left'
              }} {...props}>
                {children}
              </td>
            ),
            blockquote: ({ children, ...props }) => (
              <blockquote style={{ 
                margin: '16px 0', 
                padding: '12px 16px', 
                borderLeft: '4px solid #1890ff',
                backgroundColor: '#f0f7ff',
                borderRadius: '0 4px 4px 0'
              }} {...props}>
                {children}
              </blockquote>
            )
          }}
        >
          {markdown}
        </ReactMarkdown>
      </div>
    </Card>
  );
};

export default MarkdownViewer;
