import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Card,
  Select,
  Input,
  Button,
  Avatar,
  Empty,
  Spin,
  message,
  Menu,
  Popconfirm,
  Typography,
  Tag,
  Tooltip,
  Drawer,
  Popover,
} from 'antd';
import {
  SendOutlined,
  UserOutlined,
  RobotOutlined,
  BookOutlined,
  PlusOutlined,
  DeleteOutlined,
  MessageOutlined,
  EditOutlined,
  CopyOutlined,
  SearchOutlined,
  MenuOutlined,
  CheckOutlined,
  CloseOutlined,
} from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import { knowledgeApi } from '../services/knowledgeApi';
import type {
  KnowledgeBase,
  Conversation,
  SourceInfo,
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
  const [currentConvId, setCurrentConvId] = useState<string | null>(() => {
    // 从 localStorage 恢复上次的对话 ID
    return localStorage.getItem('knowledge_chat_conv_id');
  });
  const [convLoading, setConvLoading] = useState(false);

  // 消息状态
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [sending, setSending] = useState(false);
  const [messagesLoading, setMessagesLoading] = useState(false);

  // LLM 模型
  const [selectedModel, setSelectedModel] = useState('deepseek-chat');

  // 标题编辑状态
  const [editingConvId, setEditingConvId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');

  // 对话搜索
  const [searchKeyword, setSearchKeyword] = useState('');

  // 响应式抽屉（小屏幕）
  const [sidebarDrawerOpen, setSidebarDrawerOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

  // refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const titleInputRef = useRef<any>(null);

  // 复制状态
  const [copiedMsgId, setCopiedMsgId] = useState<string | null>(null);

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
    } catch (error) {
      console.error('加载对话列表失败:', error);
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

  // 保存当前对话 ID 到 localStorage
  useEffect(() => {
    if (currentConvId) {
      localStorage.setItem('knowledge_chat_conv_id', currentConvId);
    } else {
      localStorage.removeItem('knowledge_chat_conv_id');
    }
  }, [currentConvId]);

  // 恢复上次的对话
  useEffect(() => {
    const savedConvId = localStorage.getItem('knowledge_chat_conv_id');
    if (savedConvId && conversations.length > 0 && !currentConvId) {
      // 检查保存的对话是否还存在
      const convExists = conversations.some(c => c.id === savedConvId);
      if (convExists) {
        handleSelectConversation(savedConvId);
      } else {
        // 对话已被删除，清除 localStorage
        localStorage.removeItem('knowledge_chat_conv_id');
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversations.length]);

  // 响应式监听
  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

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

  // 开始编辑标题
  const handleStartEditTitle = (conv: Conversation, e?: React.MouseEvent) => {
    e?.stopPropagation();
    setEditingConvId(conv.id);
    setEditingTitle(conv.title || '');
    setTimeout(() => titleInputRef.current?.focus(), 50);
  };

  // 保存标题
  const handleSaveTitle = async (convId: string) => {
    if (!editingTitle.trim()) {
      message.warning('标题不能为空');
      return;
    }
    try {
      await knowledgeApi.updateConversation(convId, { title: editingTitle.trim() });
      setConversations((prev) =>
        prev.map((c) => (c.id === convId ? { ...c, title: editingTitle.trim() } : c))
      );
      setEditingConvId(null);
      message.success('标题已更新');
    } catch {
      message.error('更新失败');
    }
  };

  // 取消编辑标题
  const handleCancelEditTitle = () => {
    setEditingConvId(null);
    setEditingTitle('');
  };

  // 复制消息内容
  const handleCopyMessage = async (content: string, msgId?: string) => {
    try {
      await navigator.clipboard.writeText(content);
      message.success('已复制到剪贴板');
      if (msgId) {
        setCopiedMsgId(msgId);
        setTimeout(() => setCopiedMsgId(null), 2000);
      }
    } catch {
      message.error('复制失败');
    }
  };

  // 过滤对话列表
  const filteredConversations = conversations.filter((conv) =>
    (conv.title || '').toLowerCase().includes(searchKeyword.toLowerCase())
  );

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
        (srcList: SourceInfo[]) => {
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
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // 对话列表内容（复用于 Card 和 Drawer）
  const renderConversationList = () => (
    <>
      {/* 搜索框 */}
      <div style={{ padding: '8px 12px', borderBottom: '1px solid #f0f0f0' }}>
        <Input
          placeholder="搜索对话..."
          prefix={<SearchOutlined style={{ color: '#999' }} />}
          value={searchKeyword}
          onChange={(e) => setSearchKeyword(e.target.value)}
          allowClear
          size="small"
        />
      </div>
      {convLoading ? (
        <div style={{ textAlign: 'center', padding: 24 }}>
          <Spin />
        </div>
      ) : filteredConversations.length === 0 ? (
        <Empty description={searchKeyword ? '无匹配对话' : '暂无对话'} style={{ marginTop: 40 }} />
      ) : (
        <Menu
          mode="inline"
          selectedKeys={currentConvId ? [currentConvId] : []}
          style={{ border: 'none' }}
          items={filteredConversations.map((conv) => ({
            key: conv.id,
            icon: <MessageOutlined />,
            label:
              editingConvId === conv.id ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }} onClick={(e) => e.stopPropagation()}>
                  <Input
                    ref={titleInputRef}
                    size="small"
                    value={editingTitle}
                    onChange={(e) => setEditingTitle(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleSaveTitle(conv.id);
                      if (e.key === 'Escape') handleCancelEditTitle();
                    }}
                    onBlur={() => setTimeout(handleCancelEditTitle, 150)}
                    style={{ flex: 1 }}
                  />
                  <CheckOutlined onClick={() => handleSaveTitle(conv.id)} style={{ color: '#52c41a', cursor: 'pointer' }} />
                  <CloseOutlined onClick={handleCancelEditTitle} style={{ color: '#ff4d4f', cursor: 'pointer' }} />
                </div>
              ) : (
                <div
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                  onDoubleClick={(e) => handleStartEditTitle(conv, e)}
                >
                  <Typography.Text ellipsis style={{ flex: 1, marginRight: 8 }} title={conv.title}>
                    {conv.title || '未命名对话'}
                  </Typography.Text>
                  <div className="conv-actions" style={{ display: 'flex', gap: 8 }}>
                    <Tooltip title="编辑标题">
                      <EditOutlined
                        onClick={(e) => handleStartEditTitle(conv, e)}
                        style={{ color: '#86909c', fontSize: 16, padding: 4, cursor: 'pointer' }}
                      />
                    </Tooltip>
                    <Popconfirm
                      title="确定删除此对话？"
                      onConfirm={(e) => {
                        e?.stopPropagation();
                        handleDeleteConversation(conv.id);
                      }}
                      onCancel={(e) => e?.stopPropagation()}
                    >
                      <Tooltip title="删除对话">
                        <DeleteOutlined
                          onClick={(e) => e.stopPropagation()}
                          style={{ color: '#86909c', fontSize: 16, padding: 4, cursor: 'pointer' }}
                        />
                      </Tooltip>
                    </Popconfirm>
                  </div>
                </div>
              ),
            onClick: () => editingConvId !== conv.id && handleSelectConversation(conv.id),
          }))}
        />
      )}
    </>
  );

  return (
    <div style={{ display: 'flex', height: '100%', padding: 16, gap: 16 }}>
      {/* 移动端抽屉 */}
      <Drawer
        title="对话历史"
        placement="left"
        open={sidebarDrawerOpen}
        onClose={() => setSidebarDrawerOpen(false)}
        width={280}
        bodyStyle={{ padding: 0 }}
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => { handleNewConversation(); setSidebarDrawerOpen(false); }}>
            新建
          </Button>
        }
      >
        {renderConversationList()}
      </Drawer>

      {/* 左侧：对话历史列表（桌面端） */}
      {!isMobile && (
        <Card
          title="对话历史"
          style={{ width: 280, display: 'flex', flexDirection: 'column' }}
          bodyStyle={{ flex: 1, overflow: 'auto', padding: 0 }}
          extra={
            <Tooltip title="新建对话">
              <Button type="primary" icon={<PlusOutlined />} onClick={handleNewConversation}>
                新建
              </Button>
            </Tooltip>
          }
        >
          {renderConversationList()}
        </Card>
      )}

      {/* 右侧：聊天区域 */}
      <Card
        style={{ flex: 1, display: 'flex', flexDirection: 'column', marginLeft: isMobile ? 0 : undefined, height: '100%', overflow: 'hidden' }}
        bodyStyle={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          padding: 0,
          height: '100%',
        }}
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {isMobile && <MenuOutlined onClick={() => setSidebarDrawerOpen(true)} style={{ cursor: 'pointer' }} />}
            <span>知识问答</span>
          </div>
        }
        extra={
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
            {/* 知识库多选 */}
            <Select
              mode="multiple"
              style={{ minWidth: isMobile ? 120 : 200, maxWidth: isMobile ? 200 : 400 }}
              placeholder="选择知识库"
              loading={kbLoading}
              value={selectedKBIds}
              onChange={async (newKBIds) => {
                setSelectedKBIds(newKBIds);
                // 如果已有对话，自动更新对话设置
                if (currentConvId && newKBIds.length > 0) {
                  // 验证对话是否存在
                  const convExists = conversations.some(c => c.id === currentConvId);
                  if (!convExists) {
                    // 对话已被删除，清除状态
                    setCurrentConvId(null);
                    localStorage.removeItem('knowledge_chat_conv_id');
                    return;
                  }

                  try {
                    await knowledgeApi.updateConversation(currentConvId, { kb_ids: newKBIds });
                    setConversations((prev) =>
                      prev.map((c) => (c.id === currentConvId ? { ...c, kb_ids: newKBIds } : c))
                    );
                  } catch {
                    message.error('更新知识库失败');
                  }
                }
              }}
              maxTagCount={isMobile ? 1 : 2}
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
              style={{ width: isMobile ? 100 : 160 }}
              value={selectedModel}
              onChange={async (newModel) => {
                setSelectedModel(newModel);
                // 如果已有对话，自动更新对话设置
                if (currentConvId) {
                  // 验证对话是否存在
                  const convExists = conversations.some(c => c.id === currentConvId);
                  if (!convExists) {
                    // 对话已被删除，清除状态
                    setCurrentConvId(null);
                    localStorage.removeItem('knowledge_chat_conv_id');
                    return;
                  }

                  try {
                    await knowledgeApi.updateConversation(currentConvId, { llm_model: newModel });
                    setConversations((prev) =>
                      prev.map((c) => (c.id === currentConvId ? { ...c, llm_model: newModel } : c))
                    );
                  } catch {
                    message.error('更新模型失败');
                  }
                }
              }}
              options={LLM_MODELS.map((m) => ({
                label: m.name,
                value: m.model_id,
              }))}
            />
          </div>
        }
      >
        {/* 消息列表 - 可滚动区域 */}
        <div className="messages-scroll-container">
          {messagesLoading ? (
            <div style={{ textAlign: 'center', padding: 40 }}>
              <Spin />
            </div>
          ) : messages.length === 0 ? (
            <div className="empty-state">
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={null}
              />
              <div className="empty-guide">
                {!currentConvId ? (
                  <>
                    <div className="guide-title">开始智能问答</div>
                    <div className="guide-steps">
                      <div className="guide-step">
                        <span className="step-number">1</span>
                        <span className="step-text">选择知识库</span>
                      </div>
                      <div className="guide-arrow">→</div>
                      <div className="guide-step">
                        <span className="step-number">2</span>
                        <span className="step-text">输入问题</span>
                      </div>
                      <div className="guide-arrow">→</div>
                      <div className="guide-step">
                        <span className="step-number">3</span>
                        <span className="step-text">获取答案</span>
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="guide-title">开始提问吧</div>
                )}
              </div>
            </div>
          ) : (
            <div className="message-list">
              {messages.map((msg, index) => (
                <div
                  key={msg.id || index}
                  className={`message-item ${msg.role === 'user' ? 'message-user' : 'message-assistant'}`}
                >
                  <Avatar
                    size={36}
                    icon={msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                    className={`message-avatar ${msg.role === 'user' ? 'avatar-user' : 'avatar-assistant'}`}
                  />
                  <div className={`message-bubble ${msg.role === 'user' ? 'bubble-user' : 'bubble-assistant'}`}>
                    <div className="message-content">
                      {msg.content}
                      {msg.isStreaming && <span className="typing-cursor">|</span>}
                    </div>
                    {/* 复制按钮 */}
                    {msg.role === 'assistant' && !msg.isStreaming && msg.content && (
                      <Tooltip title={copiedMsgId === (msg.id || `msg-${index}`) ? '已复制' : '复制'}>
                        <span
                          className="copy-btn"
                          onClick={() => handleCopyMessage(msg.content, msg.id || `msg-${index}`)}
                        >
                          {copiedMsgId === (msg.id || `msg-${index}`) ? (
                            <CheckOutlined style={{ color: '#52c41a' }} />
                          ) : (
                            <CopyOutlined />
                          )}
                        </span>
                      </Tooltip>
                    )}
                    {/* 参考来源 */}
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="sources-section">
                        <div className="sources-title">
                          <BookOutlined style={{ marginRight: 6 }} />
                          参考来源
                        </div>
                        <div className="sources-list">
                          {msg.sources.map((src, idx) => (
                            <Popover
                              key={idx}
                              placement={isMobile ? 'top' : 'topLeft'}
                              trigger={isMobile ? 'click' : 'hover'}
                              overlayStyle={{ maxWidth: isMobile ? '90vw' : 480 }}
                              overlayInnerStyle={{ padding: 0 }}
                              content={
                                <div className="source-popover-content">
                                  <div className="source-popover-header">
                                    <Tag color="blue">【{src.index || idx + 1}】</Tag>
                                    <span className="source-popover-filename">{src.filename}</span>
                                    <span className="source-popover-score">
                                      {(src.score * 100).toFixed(0)}%
                                    </span>
                                  </div>
                                  <div className="source-popover-body">
                                    <ReactMarkdown
                                      rehypePlugins={[rehypeRaw]}
                                      components={{
                                        table: ({ children }) => (
                                          <table style={{ width: '100%', borderCollapse: 'collapse', border: '1px solid #e8e8e8', fontSize: 13 }}>
                                            {children}
                                          </table>
                                        ),
                                        th: ({ children }) => (
                                          <th style={{ padding: '6px 8px', border: '1px solid #e8e8e8', backgroundColor: '#f5f5f5', fontWeight: 500 }}>
                                            {children}
                                          </th>
                                        ),
                                        td: ({ children }) => (
                                          <td style={{ padding: '6px 8px', border: '1px solid #e8e8e8' }}>
                                            {children}
                                          </td>
                                        ),
                                        p: ({ children }) => (
                                          <p style={{ margin: '6px 0', lineHeight: 1.6 }}>{children}</p>
                                        ),
                                        ul: ({ children }) => (
                                          <ul style={{ margin: '6px 0', paddingLeft: 20 }}>{children}</ul>
                                        ),
                                        ol: ({ children }) => (
                                          <ol style={{ margin: '6px 0', paddingLeft: 20 }}>{children}</ol>
                                        ),
                                        li: ({ children }) => (
                                          <li style={{ margin: '2px 0' }}>{children}</li>
                                        ),
                                        code: ({ children }) => (
                                          <code style={{ padding: '1px 4px', backgroundColor: '#f0f0f0', borderRadius: 3, fontSize: 12 }}>
                                            {children}
                                          </code>
                                        ),
                                      }}
                                    >
                                      {src.text}
                                    </ReactMarkdown>
                                  </div>
                                </div>
                              }
                            >
                              <Tag className="source-tag" color="blue">
                                【{src.index || idx + 1}】{src.filename}
                              </Tag>
                            </Popover>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* 输入区域 - 固定在底部 */}
        <div className="chat-input-container">
          {/* 现代化输入框 */}
          <div className="modern-input-wrapper">
            <div className="input-glow"></div>
            <Input.TextArea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                selectedKBIds.length === 0
                  ? '请先选择知识库开始对话...'
                  : '输入您的问题，按 Enter 发送，Shift+Enter 换行...'
              }
              autoSize={{ minRows: 1, maxRows: 4 }}
              disabled={selectedKBIds.length === 0 || sending}
              className="modern-chat-input"
            />
            <button
              className={`modern-send-btn ${sending ? 'sending' : ''} ${(!inputValue.trim() || selectedKBIds.length === 0) ? 'disabled' : ''}`}
              onClick={handleSend}
              disabled={selectedKBIds.length === 0 || !inputValue.trim() || sending}
            >
              {sending ? (
                <span className="send-spinner"></span>
              ) : (
                <SendOutlined className="send-icon" />
              )}
            </button>
          </div>
        </div>
      </Card>

      {/* 完整样式 */}
      <style>{`
        /* 打字机光标 */
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

        /* 空状态引导 */
        .empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 100%;
          min-height: 300px;
        }
        .empty-guide {
          text-align: center;
          margin-top: 16px;
        }
        .guide-title {
          font-size: 18px;
          font-weight: 500;
          color: #1d2129;
          margin-bottom: 24px;
        }
        .guide-steps {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 12px;
          flex-wrap: wrap;
        }
        .guide-step {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 12px 20px;
          background: #f0f5ff;
          border-radius: 8px;
          border: 1px solid #adc6ff;
        }
        .step-number {
          width: 24px;
          height: 24px;
          background: #1890ff;
          color: white;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 14px;
          font-weight: 600;
        }
        .step-text {
          font-size: 14px;
          color: #1d2129;
        }
        .guide-arrow {
          color: #1890ff;
          font-size: 18px;
          font-weight: bold;
        }

        /* 消息列表 */
        .message-list {
          display: flex;
          flex-direction: column;
          gap: 16px;
          padding: 8px 0;
        }
        .message-item {
          display: flex;
          gap: 12px;
          max-width: 85%;
        }
        .message-user {
          flex-direction: row-reverse;
          align-self: flex-end;
        }
        .message-assistant {
          align-self: flex-start;
        }

        /* 头像 */
        .message-avatar {
          flex-shrink: 0;
        }
        .avatar-user {
          background: #1890ff !important;
        }
        .avatar-assistant {
          background: #722ed1 !important;
        }

        /* 气泡 */
        .message-bubble {
          position: relative;
          padding: 12px 16px;
          border-radius: 12px;
          line-height: 1.6;
          word-break: break-word;
        }
        .bubble-user {
          background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
          color: white;
          border-bottom-right-radius: 4px;
        }
        .bubble-assistant {
          background: #f5f7fa;
          color: #1d2129;
          border-bottom-left-radius: 4px;
          border: 1px solid #e8e8e8;
        }
        .message-content {
          white-space: pre-wrap;
        }

        /* 复制按钮 */
        .copy-btn {
          position: absolute;
          top: 8px;
          right: 8px;
          cursor: pointer;
          color: #86909c;
          font-size: 14px;
          padding: 4px;
          border-radius: 4px;
          opacity: 0;
          transition: all 0.2s;
        }
        .message-bubble:hover .copy-btn {
          opacity: 1;
        }
        .copy-btn:hover {
          color: #1890ff;
          background: rgba(24, 144, 255, 0.1);
        }

        /* 参考来源区域 */
        .sources-section {
          margin-top: 12px;
          padding-top: 12px;
          border-top: 1px dashed #d9d9d9;
        }
        .sources-title {
          font-size: 12px;
          color: #86909c;
          margin-bottom: 8px;
          display: flex;
          align-items: center;
        }
        .sources-list {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }
        .source-tag {
          cursor: pointer;
          margin: 0 !important;
          max-width: 200px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .source-tag:hover {
          opacity: 0.85;
        }

        /* 浮窗样式 - 蓝色系 */
        .source-popover-content {
          max-width: 480px;
          max-height: 400px;
          overflow: hidden;
          display: flex;
          flex-direction: column;
          border-radius: 8px;
        }
        .source-popover-header {
          padding: 12px 16px;
          background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
          color: white;
          display: flex;
          align-items: center;
          gap: 8px;
          flex-wrap: wrap;
        }
        .source-popover-header .ant-tag {
          margin: 0;
          background: rgba(255,255,255,0.2);
          border: none;
          color: white;
          font-weight: 600;
        }
        .source-popover-filename {
          font-weight: 500;
          flex: 1;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .source-popover-score {
          font-size: 12px;
          background: rgba(255,255,255,0.2);
          padding: 2px 8px;
          border-radius: 10px;
        }
        .source-popover-body {
          padding: 16px;
          max-height: 320px;
          overflow-y: auto;
          font-size: 14px;
          line-height: 1.8;
          color: #333;
          background: #fafafa;
          word-break: break-word;
        }
        .source-popover-body::-webkit-scrollbar {
          width: 6px;
        }
        .source-popover-body::-webkit-scrollbar-thumb {
          background: #ccc;
          border-radius: 3px;
        }
        .source-popover-body::-webkit-scrollbar-thumb:hover {
          background: #999;
        }

        /* 对话列表项 hover 显示操作按钮 */
        .ant-menu-item .conv-actions {
          opacity: 0;
          transition: opacity 0.2s;
        }
        .ant-menu-item:hover .conv-actions {
          opacity: 1;
        }

        /* 输入区域容器 - 固定在底部 */
        .chat-input-container {
          flex-shrink: 0;
          padding: 16px 24px 20px;
          background: #ffffff;
          border-top: 1px solid #e2e8f0;
        }

        /* 确保 Card 内部结构支持 flex */
        .ant-card {
          display: flex !important;
          flex-direction: column !important;
          height: 100% !important;
        }
        .ant-card-body {
          flex: 1 !important;
          display: flex !important;
          flex-direction: column !important;
          overflow: hidden !important;
          min-height: 0 !important;
        }

        /* 现代化输入框包装器 */
        .modern-input-wrapper {
          position: relative;
          display: flex;
          align-items: flex-end;
          background: #ffffff;
          border-radius: 16px;
          border: 2px solid #e2e8f0;
          padding: 4px;
          transition: all 0.3s ease-out;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        }
        .modern-input-wrapper:focus-within {
          border-color: #2563eb;
          box-shadow: 0 4px 20px rgba(37, 99, 235, 0.15), 0 0 0 4px rgba(37, 99, 235, 0.08);
        }
        .modern-input-wrapper:hover:not(:focus-within) {
          border-color: #94a3b8;
        }

        /* 输入框发光效果 */
        .input-glow {
          position: absolute;
          inset: -2px;
          border-radius: 18px;
          background: linear-gradient(135deg, #2563eb, #3b82f6, #60a5fa);
          opacity: 0;
          z-index: -1;
          transition: opacity 0.3s ease-out;
          filter: blur(8px);
        }
        .modern-input-wrapper:focus-within .input-glow {
          opacity: 0.15;
        }

        /* 现代化输入框 */
        .modern-chat-input {
          flex: 1;
          border: none !important;
          background: transparent !important;
          padding: 12px 16px !important;
          font-size: 15px !important;
          line-height: 1.6 !important;
          resize: none !important;
          color: #1e293b !important;
        }
        .modern-chat-input:focus {
          box-shadow: none !important;
        }
        .modern-chat-input::placeholder {
          color: #94a3b8 !important;
        }
        .modern-chat-input:disabled {
          background: transparent !important;
          cursor: not-allowed;
        }
        .modern-chat-input:disabled::placeholder {
          color: #cbd5e1 !important;
        }

        /* 现代化发送按钮 */
        .modern-send-btn {
          flex-shrink: 0;
          width: 44px;
          height: 44px;
          border-radius: 12px;
          border: none;
          background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
          color: white;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s ease-out;
          margin: 4px;
        }
        .modern-send-btn:hover:not(.disabled):not(.sending) {
          background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);
        }
        .modern-send-btn:active:not(.disabled):not(.sending) {
          transform: translateY(0);
          box-shadow: 0 2px 6px rgba(37, 99, 235, 0.3);
        }
        .modern-send-btn.disabled {
          background: #e2e8f0;
          color: #94a3b8;
          cursor: not-allowed;
        }
        .modern-send-btn.sending {
          background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
          cursor: wait;
        }
        .send-icon {
          font-size: 18px;
          transition: transform 0.2s ease-out;
        }
        .modern-send-btn:hover:not(.disabled):not(.sending) .send-icon {
          transform: translateX(2px);
        }

        /* 发送中旋转动画 */
        .send-spinner {
          width: 20px;
          height: 20px;
          border: 2px solid rgba(255, 255, 255, 0.3);
          border-top-color: white;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        /* 消息滚动容器 */
        .messages-scroll-container {
          flex: 1;
          overflow-y: auto;
          overflow-x: hidden;
          padding: 20px 24px;
          background: #f8fafc;
          min-height: 0;
        }
        .messages-scroll-container::-webkit-scrollbar {
          width: 6px;
        }
        .messages-scroll-container::-webkit-scrollbar-track {
          background: transparent;
        }
        .messages-scroll-container::-webkit-scrollbar-thumb {
          background: #cbd5e1;
          border-radius: 3px;
        }
        .messages-scroll-container::-webkit-scrollbar-thumb:hover {
          background: #94a3b8;
        }

        /* 移动端适配 */
        @media (max-width: 768px) {
          .message-item {
            max-width: 92%;
          }
          .guide-steps {
            flex-direction: column;
          }
          .guide-arrow {
            transform: rotate(90deg);
          }
          .source-popover-content {
            max-width: 90vw;
          }
        }
      `}</style>
    </div>
  );
};

export default KnowledgeChatPage;
