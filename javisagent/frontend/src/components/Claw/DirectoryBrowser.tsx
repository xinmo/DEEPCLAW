import React, { useState, useEffect } from 'react';
import { Modal, List, Button, Breadcrumb, Spin, message } from 'antd';
import { FolderOutlined, HomeOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import axios from 'axios';

interface Directory {
  name: string;
  path: string;
}

interface DirectoryBrowserProps {
  open: boolean;
  onCancel: () => void;
  onSelect: (path: string) => void;
}

const DirectoryBrowser: React.FC<DirectoryBrowserProps> = ({ open, onCancel, onSelect }) => {
  const [currentPath, setCurrentPath] = useState<string>('');
  const [parentPath, setParentPath] = useState<string | null>(null);
  const [directories, setDirectories] = useState<Directory[]>([]);
  const [loading, setLoading] = useState(false);

  // 加载目录
  const loadDirectory = async (path?: string) => {
    setLoading(true);
    try {
      const response = await axios.get('/api/claw/browse-directories', {
        params: path ? { path } : {}
      });
      setCurrentPath(response.data.current_path);
      setParentPath(response.data.parent_path);
      setDirectories(response.data.directories);
    } catch (error: any) {
      message.error(error.response?.data?.detail || '加载目录失败');
    } finally {
      setLoading(false);
    }
  };

  // 初始加载
  useEffect(() => {
    if (open) {
      loadDirectory();
    }
  }, [open]);

  // 进入子目录
  const handleEnterDirectory = (path: string) => {
    loadDirectory(path);
  };

  // 返回上级目录
  const handleGoBack = () => {
    if (parentPath) {
      loadDirectory(parentPath);
    }
  };

  // 选择当前目录
  const handleSelectCurrent = () => {
    if (currentPath) {
      onSelect(currentPath);
      onCancel();
    } else {
      message.warning('请选择一个具体的目录');
    }
  };

  return (
    <Modal
      title="选择工作目录"
      open={open}
      onCancel={onCancel}
      width={600}
      footer={[
        <Button key="back" onClick={onCancel}>
          取消
        </Button>,
        <Button
          key="select"
          type="primary"
          onClick={handleSelectCurrent}
          disabled={!currentPath}
        >
          选择当前目录
        </Button>,
      ]}
    >
      <div style={{ marginBottom: 16 }}>
        <Breadcrumb>
          <Breadcrumb.Item>
            <HomeOutlined />
          </Breadcrumb.Item>
          {currentPath && currentPath.split(/[/\\]/).filter(Boolean).map((part, index, arr) => (
            <Breadcrumb.Item key={index}>
              {index === arr.length - 1 ? part : part}
            </Breadcrumb.Item>
          ))}
        </Breadcrumb>
      </div>

      {parentPath && (
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={handleGoBack}
          style={{ marginBottom: 8 }}
        >
          返回上级
        </Button>
      )}

      <Spin spinning={loading}>
        <List
          bordered
          dataSource={directories}
          style={{ maxHeight: 400, overflow: 'auto' }}
          renderItem={(item) => (
            <List.Item
              style={{ cursor: 'pointer' }}
              onClick={() => handleEnterDirectory(item.path)}
            >
              <List.Item.Meta
                avatar={<FolderOutlined style={{ fontSize: 20, color: '#1890ff' }} />}
                title={item.name}
              />
            </List.Item>
          )}
          locale={{ emptyText: '此目录下没有子目录' }}
        />
      </Spin>

      {currentPath && (
        <div style={{ marginTop: 16, padding: 8, background: '#f5f5f5', borderRadius: 4 }}>
          <strong>当前路径：</strong> {currentPath}
        </div>
      )}
    </Modal>
  );
};

export default DirectoryBrowser;
