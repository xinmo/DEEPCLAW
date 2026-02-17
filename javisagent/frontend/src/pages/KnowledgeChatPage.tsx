import React, { useState, useEffect, useRef } from 'react';
import { Layout, List, Button, Input, Select, Card, Typography, Tag, Space, Empty, message, Popconfirm } from 'antd';
import { PlusOutlined, SendOutlined, DeleteOutlined, BookOutlined } from '@ant-design/icons';
import { knowledgeApi } from '../services/knowledgeApi';
import type { KnowledgeBase, Conversation, Message, SourceInfo } from '../types/knowledge';
import { LLM_MODELS } from '../types/knowledge';

const { Sider, Content } = Layout;
const { TextArea } = Input;
const { Text, Paragraph } = Typography;

const KnowledgeChatPage: React.FC = () => {
  const [kbs, setKBs] = useState<KnowledgeBase[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConv, setSelectedConv] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [sources, setSources] = useState<SourceInfo[]>([]);
  const [selectedKBIds, setSelectedKBIds] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState('gpt-4o');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadKBs();
    loadConversations();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  const loadKBs = async () => {
    try {
      const data = await knowledgeApi.listKBs();
      setKBs(data);
    } catch (e) {
      message.error('加载知识库失败');
    }
  };

  const loadConversations = async () => {
    try {
      const data = await knowledgeApi.listConversations();
      setConversations(data);
    } catch (e) {
      message.error('加载对话失败');
    }
  };

  const selectConversation = async (conv: Conversation) => {
    setSelectedConv(conv);
    setSelectedKBIds(conv.kb_ids);
    setSelectedModel(conv.llm_model);
    try {
      const msgs = await knowledgeApi.getMessages(conv.id);
      setMessages(msgs);
    } catch (e) {
      message.error('加载消息失败');
    }
  };

  const createConversation = async () => {
    if (selectedKBIds.length === 0) {
      message.warning('请先选择知识库');
      return;
    }
    try {
      const conv = await knowledgeApi.createConversation({
        kb_ids: selectedKBIds,
        llm_model: selectedModel,
      });
      setConversations([conv, ...conversations]);
      selectConversation(conv);
    } catch (e) {
      message.error('创建对话失败');
    }
  };

  const deleteConversation = async (convId: string) => {
    try {
      await knowledgeApi.deleteConversation(convId);
      setConversations(conversations.filter(c => c.id !== convId));
      if (selectedConv?.id === convId) {
        setSelectedConv(null);
        setMessages([]);
      }
    } catch (e) {
      message.error('删除失败');
    }
  };

  const sendMessage = async () => {
    if (!selectedConv || !inputValue.trim() || streaming) return;
    const content = inputValue.trim();
    setInputValue('');
    setMessages([...messages, { id: 'temp', conversation_id: selectedConv.id, role: 'user', content, sources: [], created_at: new Date().toISOString() }]);
    setStreaming(true);
    setStreamingContent('');
    setSources([]);

    try {
      await knowledgeApi.sendMessage(
        selectedConv.id,
        { content },
        (chunk) => setStreamingContent(prev => prev + chunk),
        (srcs) => setSources(srcs),
        () => {
          setStreaming(false);
          knowledgeApi.getMessages(selectedConv.id).then(setMessages);
        }
      );
    } catch (e) {
      message.error('发送失败');
      setStreaming(false);
    }
  };

  return (
    <Layout style={{ height: 'calc(100vh - 64px)', background: '#fff' }}>
      <Sider width={280} style={{ background: '#f5f5f5', padding: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Select mode="multiple" placeholder="选择知识库" style={{ width: '100%' }} value={selectedKBIds} onChange={setSelectedKBIds}
            options={kbs.map(kb => ({ label: kb.name, value: kb.id }))} />
          <Select placeholder="选择模型" style={{ width: '100%' }} value={selectedModel} onChange={setSelectedModel}
            options={LLM_MODELS.map(m => ({ label: m.name, value: m.model_id }))} />
          <Button type="primary" icon={<PlusOutlined />} block onClick={createConversation}>新建对话</Button>
        </Space>
        <List style={{ marginTop: 16 }} dataSource={conversations} renderItem={conv => (
          <List.Item style={{ cursor: 'pointer', background: selectedConv?.id === conv.id ? '#e6f7ff' : 'transparent', padding: '8px 12px', borderRadius: 4 }}
            onClick={() => selectConversation(conv)}
            actions={[<Popconfirm title="确定删除？" onConfirm={(e) => { e?.stopPropagation(); deleteConversation(conv.id); }}>
              <DeleteOutlined onClick={e => e.stopPropagation()} />
            </Popconfirm>]}>
            <List.Item.Meta title={conv.title} description={new Date(conv.updated_at).toLocaleString()} />
          </List.Item>
        )} />
      </Sider>
      <Content style={{ padding: 24, display: 'flex', flexDirection: 'column' }}>
        {selectedConv ? (
          <>
            <div style={{ flex: 1, overflow: 'auto', marginBottom: 16 }}>
              {messages.map((msg, idx) => (
                <div key={msg.id || idx} style={{ marginBottom: 16, textAlign: msg.role === 'user' ? 'right' : 'left' }}>
                  <Card size="small" style={{ display: 'inline-block', maxWidth: '70%', textAlign: 'left', background: msg.role === 'user' ? '#1890ff' : '#f0f0f0', color: msg.role === 'user' ? '#fff' : '#000' }}>
                    <Paragraph style={{ margin: 0, whiteSpace: 'pre-wrap', color: 'inherit' }}>{msg.content}</Paragraph>
                    {msg.sources?.length > 0 && (
                      <div style={{ marginTop: 8, borderTop: '1px solid #ddd', paddingTop: 8 }}>
                        <Text type="secondary" style={{ fontSize: 12 }}>来源：</Text>
                        {msg.sources.map((s, i) => <Tag key={i} color="blue" style={{ marginTop: 4 }}>{s.filename}</Tag>)}
                      </div>
                    )}
                  </Card>
                </div>
              ))}
              {streaming && streamingContent && (
                <div style={{ marginBottom: 16 }}>
                  <Card size="small" style={{ display: 'inline-block', maxWidth: '70%', background: '#f0f0f0' }}>
                    <Paragraph style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{streamingContent}</Paragraph>
                  </Card>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <TextArea value={inputValue} onChange={e => setInputValue(e.target.value)} placeholder="输入问题..." autoSize={{ minRows: 1, maxRows: 4 }}
                onPressEnter={e => { if (!e.shiftKey) { e.preventDefault(); sendMessage(); } }} />
              <Button type="primary" icon={<SendOutlined />} onClick={sendMessage} loading={streaming}>发送</Button>
            </div>
          </>
        ) : (
          <Empty description="选择或创建一个对话" style={{ margin: 'auto' }} />
        )}
      </Content>
    </Layout>
  );
};

export default KnowledgeChatPage;
