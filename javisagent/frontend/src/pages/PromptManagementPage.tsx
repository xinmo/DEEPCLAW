import React, { useState, useEffect } from 'react';
import { Layout, Menu, Input, Button, message, Space, Typography } from 'antd';
import { promptApi, type PromptInfo, type PromptDetail } from '../services/promptApi';

const { Sider, Content } = Layout;
const { TextArea } = Input;
const { Title, Text } = Typography;

const PromptManagementPage: React.FC = () => {
  const [prompts, setPrompts] = useState<PromptInfo[]>([]);
  const [selectedPromptId, setSelectedPromptId] = useState<string>('');
  const [promptDetail, setPromptDetail] = useState<PromptDetail | null>(null);
  const [content, setContent] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  // 加载提示词列表
  useEffect(() => {
    loadPrompts();
  }, []);

  // 当选中提示词变化时，加载详情
  useEffect(() => {
    if (selectedPromptId) {
      loadPromptDetail(selectedPromptId);
    }
  }, [selectedPromptId]);

  const loadPrompts = async () => {
    try {
      setLoading(true);
      const data = await promptApi.getPrompts();
      setPrompts(data.prompts);

      // 默认选中第一个
      if (data.prompts.length > 0) {
        setSelectedPromptId(data.prompts[0].id);
      }
    } catch (error) {
      message.error('加载提示词列表失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const loadPromptDetail = async (id: string) => {
    try {
      setLoading(true);
      const detail = await promptApi.getPromptDetail(id);
      setPromptDetail(detail);
      setContent(detail.content);
    } catch (error) {
      message.error('加载提示词详情失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!content.trim()) {
      message.error('提示词不能为空');
      return;
    }

    try {
      setSaving(true);
      await promptApi.updatePrompt(selectedPromptId, content);
      message.success('保存成功，新对话将使用此提示词');

      // 重新加载详情
      await loadPromptDetail(selectedPromptId);
    } catch (error: any) {
      message.error(error.response?.data?.detail || '保存失败');
      console.error(error);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    try {
      setSaving(true);
      const result = await promptApi.resetPrompt(selectedPromptId);
      setContent(result.content);
      message.success('已重置为默认提示词');

      // 重新加载详情
      await loadPromptDetail(selectedPromptId);
    } catch (error: any) {
      message.error(error.response?.data?.detail || '重置失败');
      console.error(error);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Layout style={{ height: '100vh' }}>
      <Sider width={200} theme="light" style={{ borderRight: '1px solid #f0f0f0' }}>
        <div style={{ padding: '16px', borderBottom: '1px solid #f0f0f0' }}>
          <Title level={5} style={{ margin: 0 }}>提示词管理</Title>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedPromptId]}
          items={prompts.map(prompt => ({
            key: prompt.id,
            label: prompt.name,
            onClick: () => setSelectedPromptId(prompt.id),
          }))}
        />
      </Sider>
      <Content style={{ padding: '24px', overflow: 'auto' }}>
        {promptDetail && (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <div>
              <Title level={4}>{promptDetail.name}</Title>
              <Text type="secondary">编辑后保存，新对话将使用此提示词</Text>
            </div>

            <TextArea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={20}
              placeholder="请输入系统提示词"
              style={{ fontFamily: 'monospace' }}
            />

            <Space>
              <Button
                type="primary"
                onClick={handleSave}
                loading={saving}
              >
                保存
              </Button>
              <Button
                onClick={handleReset}
                loading={saving}
              >
                重置为默认
              </Button>
            </Space>
          </Space>
        )}
      </Content>
    </Layout>
  );
};

export default PromptManagementPage;
