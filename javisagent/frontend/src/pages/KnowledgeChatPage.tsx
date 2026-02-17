import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Card,
  Select,
  Input,
  Button,
  List,
  Avatar,
  Empty,
  Spin,
  message,
  Menu,
  Popconfirm,
  Typography,
  Tag,
  Tooltip,
} from 'antd';
import {
  SendOutlined,
  UserOutlined,
  RobotOutlined,
  BookOutlined,
  PlusOutlined,
  DeleteOutlined,
  MessageOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { knowledgeApi } from '../services/knowledgeApi';
import type {
  KnowledgeBase,
  Conversation,
  SourceInfo,
  SSEEvent,
} from '../types/knowledge';
import { LLM_MODELS } from '../types/knowledge';

// 聊天消息显示类型（包含流式状态）
interface ChatMessage {
  id?: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: SourceInfo[];
  isStreaming?: boolean;
}

const KnowledgeChatPage: React.FC = () => {
  // 知识库状态
  const [kbs, setKBs] = useState<KnowledgeBase[]>([]);
  const [selectedKBIds, setSelectedKBIds] = useState<string[]>([]);
  const [kbLoading, setKBLoading] = useState(false);

  // 对话状态
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConvId, setCurrentConvId] = useState<string | null>(null);
  const [convLoading, setConvLoading] = useState(false);

  // 消息状态
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [sending, setSending] = useState(false);
  const [messagesLoading, setMessagesLoading] = useState(false);

  // LLM 模型
  const [selectedModel, setSelectedModel] = useState('gpt-4o-mini');

  // refs
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 加载知识库列表
  const loadKBs = useCallback(async () => {
    setKBLoading(true);
    try {
      const data = await knowledgeApi.listKBs();
      setKBs(data);
    } catch {
      message.error('加载知识库列表失败');
    } finally {
      setKBLoading(false);
    }
  }, []);

  // 加载对话列表
  const loadConversations = useCallback(async () => {
    setConvLoading(true);
    try {
      const data = await knowledgeApi.listConversations();
      setConversations(data);
    } catch {
      message.error('加载对话列表失败');
    } finally {
      setConvLoading(false);
    }
  }, []);

  // 加载对话消息
  const loadMessages = useCallback(async (convId: string) => {
    setMessagesLoading(true);
    try {
      const data = await knowledgeApi.getMessages(convId);
      setMessages(
        data.map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          sources: m.sources,
        }))
      );
    } catch {
      message.error('加载消息失败');
    } finally {
      setMessagesLoading(false);
    }
  }, []);

  // 初始化
  useEffect(() => {
    loadKBs();
    loadConversations();
  }, [loadKBs, loadConversations]);

  // 滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 选择对话
  const handleSelectConversation = async (convId: string) => {
    if (convId === currentConvId) return;
    setCurrentConvId(convId);
    setMessages([]);

    // 加载对话详情和消息
    try {
      const conv = await knowledgeApi.getConversation(convId);
      setSelectedKBIds(conv.kb_ids);
      setSelectedModel(conv.llm_model || 'gpt-4o-mini');
      await loadMessages(convId);
    } catch {
      message.error('加载对话失败');
    }
  };

  // 新建对话
  const handleNewConversation = async () => {
    if (selectedKBIds.length === 0) {
      message.warning('请先选择至少一个知识库');
      return;
    }

    try {
      const conv = await knowledgeApi.createConversation({
        kb_ids: selectedKBIds,
        title: '新对话',
        llm_model: selectedModel,
      });
      setConversations((prev) => [conv, ...prev]);
      setCurrentConvId(conv.id);
      setMessages([]);
      message.success('新建对话成功');
    } catch {
      message.error('新建对话失败');
    }
  };

  // 删除对话
  const handleDeleteConversation = async (convId: string) => {
    try {
      await knowledgeApi.deleteConversation(convId);
      setConversations((prev) => prev.filter((c) => c.id !== convId));
      if (currentConvId === convId) {
        setCurrentConvId(null);
        setMessages([]);
      }
      message.success('删除成功');
    } catch {
      message.error('删除失败');
    }
  };

  // 发送消息（SSE 流式）
  const handleSend = async () => {
    if (!inputValue.trim()) {
      message.warning('请输入问题');
      return;
    }

    // 如果没有当前对话，先创建一个
    let convId = currentConvId;
    if (!convId) {
      if (selectedKBIds.length === 0) {
        message.warning('请先选择知识库');
        return;
      }
      try {
        const conv = await knowledgeApi.createConversation({
          kb_ids: selectedKBIds,
          title: inputValue.trim().slice(0, 20) + '...',
          llm_model: selectedModel,
        });
        setConversations((prev) => [conv, ...prev]);
        setCurrentConvId(conv.id);
        convId = conv.id;
      } catch {
        message.error('创建对话失败');
        return;
      }
    }

    const userMessage: ChatMessage = {
      role: 'user',
      content: inputValue.trim(),
    };

    // 添加用户消息和空的助手消息（用于流式填充）
    setMessages((prev) => [
      ...prev,
      userMessage,
      { role: 'assistant', content: '', isStreaming: true },
    ]);
    setInputValue('');
    setSending(true);

    let assistantContent = '';
    let sources: SourceInfo[] = [];

    try {
      await knowledgeApi.sendMessage(
        convId,
        { content: userMessage.content },
        // onChunk - 流式内容
        (chunk: string) => {
          assistantContent += chunk;
          setMessages((prev) => {
            const newMessages = [...prev];
            const lastMsg = newMessages[newMessages.length - 1];
            if (lastMsg.role === 'assistant') {
              lastMsg.content = assistantContent;
            }
            return newMessages;
          });
        },
        // onSources - 参考来源
        (srcList: SSEEvent['sources']) => {
          if (srcList) {
            sources = srcList;
          }
        },
        // onDone - 完成
        () => {
          setMessages((prev) => {
            const newMessages = [...prev];
            const lastMsg = newMessages[newMessages.length - 1];
            if (lastMsg.role === 'assistant') {
              lastMsg.isStreaming = false;
              lastMsg.sources = sources;
            }
            return newMessages;
          });
        }
      );
    } catch {
      message.error('发送消息失败');
      // 移除失败的助手消息
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setSending(false);
    }
  };

  // 按键处理
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // 获取知识库名称
  const getKBName = (kbId: string) => {
    const kb = kbs.find((k) => k.id === kbId);
    return kb?.name || kbId;
  };

  return (
    <div style={{ display: 'flex', height: '100%', padding: 16, gap: 16 }}>
      {/* 左侧：对话历史列表 */}
      <Card
        title="对话历史"
        style={{ width: 280, display: 'flex', flexDirection: 'column' }}
        bodyStyle={{ flex: 1, overflow: 'auto', padding: 0 }}
        extra={
          <Tooltip title="新建对话">
            <Button
              type="primary"
              size="small"
              icon={<PlusOutlined />}
              onClick={handleNewConversation}
            />
          </Tooltip>
        }
      >
        {convLoading ? (
          <div style={{ textAlign: 'center', padding: 24 }}>
            <Spin />
          </div>
        ) : conversations.length === 0 ? (
          <Empty description="暂无对话" style={{ marginTop: 40 }} />
        ) : (
          <Menu
            mode="inline"
            selectedKeys={currentConvId ? [currentConvId] : []}
            style={{ border: 'none' }}
            items={conversations.map((conv) => ({
              key: conv.id,
              icon: <MessageOutlined />,
              label: (
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <Typography.Text
                    ellipsis
                    style={{ flex: 1, marginRight: 8 }}
                    title={conv.title}
                  >
                    {conv.title || '未命名对话'}
                  </Typography.Text>
                  <Popconfirm
                    title="确定删除此对话？"
                    onConfirm={(e) => {
                      e?.stopPropagation();
                      handleDeleteConversation(conv.id);
                    }}
                    onCancel={(e) => e?.stopPropagation()}
                  >
                    <DeleteOutlined
                      onClick={(e) => e.stopPropagation()}
                      style={{ color: '#999' }}
                    />
                  </Popconfirm>
                </div>
              ),
              onClick: () => handleSelectConversation(conv.id),
            }))}
          />
        )}
      </Card>

      {/* 右侧：聊天区域 */}
      <Card
        style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
        bodyStyle={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span>知识问答</span>
            <SettingOutlined style={{ color: '#999' }} />
          </div>
        }
        extra={
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            {/* 知识库多选 */}
            <Select
              mode="multiple"
              style={{ minWidth: 200, maxWidth: 400 }}
              placeholder="选择知识库"
              loading={kbLoading}
              value={selectedKBIds}
              onChange={setSelectedKBIds}
              maxTagCount={2}
              options={kbs.map((kb) => ({
                label: (
                  <span>
                    <BookOutlined /> {kb.name}
                  </span>
                ),
                value: kb.id,
              }))}
            />
            {/* LLM 模型选择 */}
            <Select
              style={{ width: 160 }}
              value={selectedModel}
              onChange={setSelectedModel}
              options={LLM_MODELS.map((m) => ({
                label: m.name,
                value: m.model_id,
              }))}
            />
          </div>
        }
      >
        {/* 当前对话的知识库标签 */}
        {currentConvId && selectedKBIds.length > 0 && (
          <div style={{ marginBottom: 12 }}>
            {selectedKBIds.map((kbId) => (
              <Tag key={kbId} color="blue" icon={<BookOutlined />}>
                {getKBName(kbId)}
              </Tag>
            ))}
          </div>
        )}

        {/* 消息列表 */}
        <div style={{ flex: 1, overflow: 'auto', marginBottom: 16 }}>
          {messagesLoading ? (
            <div style={{ textAlign: 'center', padding: 40 }}>
              <Spin tip="加载消息中..." />
            </div>
          ) : messages.length === 0 ? (
            <Empty
              description={
                currentConvId
                  ? '开始提问吧'
                  : '选择知识库后开始新对话'
              }
              style={{ marginTop: 100 }}
            />
          ) : (
            <List
              dataSource={messages}
              renderItem={(msg, index) => (
                <List.Item
                  key={msg.id || index}
                  style={{ border: 'none', padding: '12px 0' }}
                >
                  <List.Item.Meta
                    avatar={
                      <Avatar
                        icon={
                          msg.role === 'user' ? (
                            <UserOutlined />
                          ) : (
                            <RobotOutlined />
                          )
                        }
                        style={{
                          backgroundColor:
                            msg.role === 'user' ? '#1890ff' : '#52c41a',
                        }}
                      />
                    }
                    title={msg.role === 'user' ? '你' : '助手'}
                    description={
                      <div>
                        <div
                          style={{
                            whiteSpace: 'pre-wrap',
                            lineHeight: 1.6,
                          }}
                        >
                          {msg.content}
                          {msg.isStreaming && (
                            <span className="typing-cursor">|</span>
                          )}
                        </div>
                        {/* 参考来源 */}
                        {msg.sources && msg.sources.length > 0 && (
                          <div
                            style={{
                              marginTop: 12,
                              padding: 12,
                              background: '#f5f5f5',
                              borderRadius: 6,
                              fontSize: 12,
                            }}
                          >
                            <div
                              style={{
                                fontWeight: 500,
                                marginBottom: 8,
                                color: '#666',
                              }}
                            >
                              参考来源：
                            </div>
                            {msg.sources.map((src, idx) => (
                              <div
                                key={idx}
                                style={{
                                  marginBottom: 4,
                                  color: '#888',
                                }}
                              >
                                <Tag color="geekblue" style={{ marginRight: 8 }}>
                                  {idx + 1}
                                </Tag>
                                {src.filename}
                                <span style={{ marginLeft: 8, color: '#aaa' }}>
                                  相似度: {(src.score * 100).toFixed(1)}%
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    }
                  />
                </List.Item>
              )}
            />
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* 输入区域 */}
        <div style={{ display: 'flex', gap: 8 }}>
          <Input.TextArea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={
              selectedKBIds.length === 0
                ? '请先选择知识库...'
                : '输入你的问题，按 Enter 发送...'
            }
            autoSize={{ minRows: 1, maxRows: 4 }}
            disabled={selectedKBIds.length === 0 || sending}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            loading={sending}
            disabled={
              selectedKBIds.length === 0 || !inputValue.trim() || sending
            }
          >
            发送
          </Button>
        </div>
      </Card>

      {/* 打字机光标动画样式 */}
      <style>{`
        .typing-cursor {
          display: inline-block;
          animation: blink 1s infinite;
          color: #1890ff;
          font-weight: bold;
        }
        @keyframes blink {
          0%, 50% { opacity: 1; }
          51%, 100% { opacity: 0; }
        }
      `}</style>
    </div>
  );
};

export default KnowledgeChatPage;
