import React, { useEffect, useState } from 'react';
import {
  Button,
  Divider,
  Grid,
  Input,
  Space,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  promptApi,
  type PromptDetail,
  type PromptInfo,
} from '../services/promptApi';

const { useBreakpoint } = Grid;
const { TextArea } = Input;
const { Paragraph, Text, Title } = Typography;

const PromptManagementPage: React.FC = () => {
  const screens = useBreakpoint();
  const isNarrowLayout = !screens.lg;
  const [prompts, setPrompts] = useState<PromptInfo[]>([]);
  const [selectedPromptId, setSelectedPromptId] = useState<string>('');
  const [promptDetail, setPromptDetail] = useState<PromptDetail | null>(null);
  const [content, setContent] = useState<string>('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    void loadPrompts();
  }, []);

  useEffect(() => {
    if (selectedPromptId) {
      void loadPromptDetail(selectedPromptId);
    }
  }, [selectedPromptId]);

  const loadPrompts = async () => {
    try {
      const data = await promptApi.getPrompts();
      setPrompts(data.prompts);
      if (data.prompts.length > 0) {
        setSelectedPromptId((current) => current || data.prompts[0].id);
      }
    } catch (error) {
      message.error('Failed to load prompt list.');
      console.error(error);
    }
  };

  const loadPromptDetail = async (id: string) => {
    try {
      const detail = await promptApi.getPromptDetail(id);
      setPromptDetail(detail);
      setContent(detail.content);
    } catch (error) {
      message.error('Failed to load prompt detail.');
      console.error(error);
    }
  };

  const handleSave = async () => {
    if (!selectedPromptId) {
      return;
    }

    if (!content.trim()) {
      message.error('Prompt content cannot be empty.');
      return;
    }

    try {
      setSaving(true);
      await promptApi.updatePrompt(selectedPromptId, content);
      message.success('Saved. New runs will use the updated prompt.');
      await loadPromptDetail(selectedPromptId);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || 'Failed to save prompt.');
      console.error(error);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!selectedPromptId) {
      return;
    }

    try {
      setSaving(true);
      const result = await promptApi.resetPrompt(selectedPromptId);
      setContent(result.content);
      message.success('Reset to default.');
      await loadPromptDetail(selectedPromptId);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || 'Failed to reset prompt.');
      console.error(error);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: isNarrowLayout ? 'minmax(0, 1fr)' : '320px minmax(0, 1fr)',
        gap: 24,
        alignItems: 'start',
      }}
    >
      <div
        style={{
          border: '1px solid #f0f0f0',
          borderRadius: 12,
          overflow: 'hidden',
          background: '#fafafa',
          minWidth: 0,
        }}
      >
        <div style={{ padding: 16, borderBottom: '1px solid #f0f0f0' }}>
          <Title level={5} style={{ margin: 0 }}>
            Prompt Management
          </Title>
          <Text type="secondary">
            First-stage DeepAgents prompt surfaces are now editable here.
          </Text>
        </div>
        <div style={{ padding: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
          {prompts.map((prompt) => {
            const isSelected = prompt.id === selectedPromptId;

            return (
              <button
                key={prompt.id}
                type="button"
                onClick={() => setSelectedPromptId(prompt.id)}
                style={{
                  width: '100%',
                  textAlign: 'left',
                  padding: '12px 14px',
                  borderRadius: 10,
                  appearance: 'none',
                  border: isSelected ? '1px solid #91caff' : '1px solid transparent',
                  background: isSelected ? '#e6f4ff' : '#fff',
                  fontFamily: 'inherit',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                }}
              >
                <div
                  style={{
                    fontSize: 14,
                    fontWeight: 600,
                    color: '#1f1f1f',
                    lineHeight: 1.4,
                    wordBreak: 'break-word',
                  }}
                >
                  {prompt.name}
                </div>
                <div
                  style={{
                    marginTop: 4,
                    fontSize: 12,
                    color: '#8c8c8c',
                    lineHeight: 1.5,
                    wordBreak: 'break-word',
                  }}
                >
                  {prompt.description}
                </div>
              </button>
            );
          })}
        </div>
      </div>
      <div
        style={{
          minWidth: 0,
          border: '1px solid #f0f0f0',
          borderRadius: 12,
          background: '#fff',
          padding: isNarrowLayout ? 16 : 24,
        }}
      >
        {promptDetail ? (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <div>
              <Title level={4} style={{ marginTop: 0 }}>
                {promptDetail.name}
              </Title>
              <Paragraph type="secondary" style={{ maxWidth: 900 }}>
                {promptDetail.description}
              </Paragraph>
              {promptDetail.variables.length > 0 && (
                <Space wrap>
                  <Text type="secondary">Template variables:</Text>
                  {promptDetail.variables.map((variable) => (
                    <Tag key={variable}>{`{${variable}}`}</Tag>
                  ))}
                </Space>
              )}
            </div>

            <div>
              <Text strong>Current content</Text>
              <Divider style={{ margin: '8px 0 16px' }} />
              <TextArea
                value={content}
                onChange={(event) => setContent(event.target.value)}
                autoSize={{ minRows: isNarrowLayout ? 16 : 22, maxRows: 32 }}
                style={{ fontFamily: 'monospace' }}
              />
            </div>

            <Space>
              <Button type="primary" onClick={handleSave} loading={saving}>
                Save
              </Button>
              <Button onClick={handleReset} loading={saving}>
                Reset to default
              </Button>
            </Space>
          </Space>
        ) : (
          <Text type="secondary">Select a prompt from the left panel.</Text>
        )}
      </div>
    </div>
  );
};

export default PromptManagementPage;
