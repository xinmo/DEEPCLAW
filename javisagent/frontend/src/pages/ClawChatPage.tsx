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
  Tooltip,
  Drawer,
} from 'antd';
import {
  SendOutlined,
  UserOutlined,
  RobotOutlined,
  FolderOutlined,
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
import { clawApi } from '../services/clawApi';
import type {
  ClawConversation,
  ClawMessage,
  ModelInfo,
  SSEEvent,
  ToolCall,
  SubAgent,
  PlanningTask,
} from '../types/claw';
import ToolCallCard from '../components/Claw/ToolCallCard';
import SubAgentCard from '../components/Claw/SubAgentCard';
import PlanningCard from '../components/Claw/PlanningCard';

// 聊天消息显示类型（包含流式状态）
interface ChatMessage {
  id?: string;
  role: 'user' | 'assistant';
  content: string;
  toolCalls?: ToolCall[];
  subAgents?: SubAgent[];
  planningTasks?: PlanningTask[];
  isStreaming?: boolean;
}

const ClawChatPage: React.FC = () => {
  // 对话状态
  const [conversations, setConversations] = useState<ClawConversation[]>([]);
  const [currentConvId, setCurrentConvId] = useState<string | null>(() => {
    return localStorage.getItem('claw_chat_conv_id');
  });
  const [convLoading, setConvLoading] = useState(false);

  // 消息状态
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [sending, setSending] = useState(false);
  const [messagesLoading, setMessagesLoading] = useState(false);

  // 配置状态
  const [workingDirectory, setWorkingDirectory] = useState('');
  const [selectedModel, setSelectedModel] = useState('claude-opus-4-6');
  const [models, setModels] = useState<ModelInfo[]>([]);

  // 编辑状态
  const [editingConvId, setEditingConvId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');

  // 搜索
  const [searchKeyword, setSearchKeyword] = useState('');

  // 响应式
  const [sidebarDrawerOpen, setSidebarDrawerOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

  // 新建对话
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [createForm] = Form.useForm();

  // 加载对话列表
  const loadConversations = useCallback(async () => {
    setConvLoading(true);
    try {
      const data = await clawApi.listConversations();
      setConversations(data);
    } catch (error) {
      message.error('加载对话列表失败');
    } finally {
      setConvLoading(false);
    }
  }, []);

  // 加载模型列表
  const loadModels = useCallback(async () => {
    try {
      const data = await clawApi.listModels();
      setModels(data);
    } catch (error) {
      message.error('加载模型列表失败');
    }
  }, []);

  // 初始化
  useEffect(() => {
    loadConversations();
    loadModels();
  }, [loadConversations, loadModels]);

  // 保存当前对话 ID
  useEffect(() => {
    if (currentConvId) {
      localStorage.setItem('claw_chat_conv_id', currentConvId);
    } else {
      localStorage.removeItem('claw_chat_conv_id');
    }
  }, [currentConvId]);

  // 响应式监听
  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // 加载消息历史
  useEffect(() => {
    if (!currentConvId) {
      setMessages([]);
      return;
    }

    const loadMessages = async () => {
      setMessagesLoading(true);
      try {
        const data = await clawApi.getMessages(currentConvId);
        setMessages(data.map(msg => ({
          id: msg.id,
          role: msg.role,
          content: msg.content,
          isStreaming: false
        })));
      } catch (error) {
        message.error('加载消息失败');
      } finally {
        setMessagesLoading(false);
      }
    };

    loadMessages();
  }, [currentConvId]);

  // 发送消息
  const handleSendMessage = async () => {
    if (!currentConvId || !inputValue.trim()) return;

    const userMessage = inputValue.trim();
    setInputValue('');
    setSending(true);

    // 添加用户消息
    const userMsg: ChatMessage = {
      role: 'user',
      content: userMessage,
      isStreaming: false
    };
    setMessages(prev => [...prev, userMsg]);

    // 添加 Assistant 占位消息
    const assistantMsg: ChatMessage = {
      role: 'assistant',
      content: '',
      isStreaming: true
    };
    setMessages(prev => [...prev, assistantMsg]);

    try {
      let assistantContent = '';
      const toolCalls: ToolCall[] = [];
      const subAgents: SubAgent[] = [];
      let planningTasks: PlanningTask[] = [];

      await clawApi.sendMessage(
        currentConvId,
        { content: userMessage },
        (event: SSEEvent) => {
          if (event.type === 'text') {
            assistantContent += event.content;
            setMessages(prev => {
              const newMessages = [...prev];
              const lastMsg = newMessages[newMessages.length - 1];
              if (lastMsg.role === 'assistant') {
                lastMsg.content = assistantContent;
              }
              return newMessages;
            });
          } else if (event.type === 'tool_call') {
            // 工具调用开始
            const toolCall: ToolCall = {
              id: event.tool_id || `tool_${Date.now()}`,
              toolName: event.tool_name,
              status: 'running',
              input: event.tool_input
            };
            toolCalls.push(toolCall);
            setMessages(prev => {
              const newMessages = [...prev];
              const lastMsg = newMessages[newMessages.length - 1];
              if (lastMsg.role === 'assistant') {
                lastMsg.toolCalls = [...toolCalls];
              }
              return newMessages;
            });
          } else if (event.type === 'tool_result') {
            // 工具调用结果
            const toolCall = toolCalls.find(t => t.toolName === event.tool_name);
            if (toolCall) {
              toolCall.status = event.status || 'success';
              toolCall.output = event.output;
              toolCall.duration = event.duration;
              toolCall.error = event.error;
              setMessages(prev => {
                const newMessages = [...prev];
                const lastMsg = newMessages[newMessages.length - 1];
                if (lastMsg.role === 'assistant') {
                  lastMsg.toolCalls = [...toolCalls];
                }
                return newMessages;
              });
            }
          } else if (event.type === 'subagent_start') {
            // 子智能体启动
            const subAgent: SubAgent = {
              id: event.agent_id,
              name: event.agent_name,
              task: event.task,
              status: 'running',
              progress: 0
            };
            subAgents.push(subAgent);
            setMessages(prev => {
              const newMessages = [...prev];
              const lastMsg = newMessages[newMessages.length - 1];
              if (lastMsg.role === 'assistant') {
                lastMsg.subAgents = [...subAgents];
              }
              return newMessages;
            });
          } else if (event.type === 'subagent_progress') {
            // 子智能体进度
            const subAgent = subAgents.find(s => s.id === event.agent_id);
            if (subAgent) {
              subAgent.progress = event.progress;
              setMessages(prev => {
                const newMessages = [...prev];
                const lastMsg = newMessages[newMessages.length - 1];
                if (lastMsg.role === 'assistant') {
                  lastMsg.subAgents = [...subAgents];
                }
                return newMessages;
              });
            }
          } else if (event.type === 'subagent_complete') {
            // 子智能体完成
            const subAgent = subAgents.find(s => s.id === event.agent_id);
            if (subAgent) {
              subAgent.status = 'success';
              subAgent.result = event.result;
              subAgent.duration = event.duration;
              setMessages(prev => {
                const newMessages = [...prev];
                const lastMsg = newMessages[newMessages.length - 1];
                if (lastMsg.role === 'assistant') {
                  lastMsg.subAgents = [...subAgents];
                }
                return newMessages;
              });
            }
          } else if (event.type === 'planning') {
            // 规划任务
            planningTasks = event.tasks || [];
            setMessages(prev => {
              const newMessages = [...prev];
              const lastMsg = newMessages[newMessages.length - 1];
              if (lastMsg.role === 'assistant') {
                lastMsg.planningTasks = [...planningTasks];
              }
              return newMessages;
            });
          } else if (event.type === 'done') {
            setMessages(prev => {
              const newMessages = [...prev];
              const lastMsg = newMessages[newMessages.length - 1];
              if (lastMsg.role === 'assistant') {
                lastMsg.isStreaming = false;
              }
              return newMessages;
            });
          } else if (event.type === 'error') {
            message.error(event.message || '发送消息失败');
          }
        },
        (error) => {
          message.error('连接失败: ' + error.message);
        }
      );
    } catch (error: any) {
      message.error(error.message || '发送消息失败');
      // 移除失败的 Assistant 消息
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setSending(false);
    }
  };

  // 过滤对话
  const filteredConversations = conversations.filter((conv) =>
    conv.title.toLowerCase().includes(searchKeyword.toLowerCase())
  );

  // 创建新对话
  const handleCreateConversation = async () => {
    try {
      const values = await createForm.validateFields();
      const newConv = await clawApi.createConversation({
        title: values.title || '新对话',
        working_directory: values.working_directory,
        llm_model: values.llm_model || 'claude-opus-4-6'
      });
      message.success('对话创建成功');
      setCreateModalOpen(false);
      createForm.resetFields();
      await loadConversations();
      setCurrentConvId(newConv.id);
      setWorkingDirectory(newConv.working_directory);
      setSelectedModel(newConv.llm_model);
    } catch (error: any) {
      if (error.errorFields) {
        // 表单验证错误
        return;
      }
      message.error(error.message || '创建对话失败');
    }
  };

  // 删除对话
  const handleDeleteConversation = async (convId: string) => {
    try {
      await clawApi.deleteConversation(convId);
      message.success('对话已删除');
      await loadConversations();
      if (currentConvId === convId) {
        setCurrentConvId(null);
      }
    } catch (error) {
      message.error('删除对话失败');
    }
  };

  // 对话列表渲染
  const renderConversationList = () => (
    <>
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
            label: (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>{conv.title}</span>
                <Popconfirm
                  title="确定删除此对话？"
                  onConfirm={(e) => {
                    e?.stopPropagation();
                    handleDeleteConversation(conv.id);
                  }}
                  okText="删除"
                  cancelText="取消"
                >
                  <DeleteOutlined
                    style={{ color: '#ff4d4f' }}
                    onClick={(e) => e.stopPropagation()}
                  />
                </Popconfirm>
              </div>
            ),
            onClick: () => setCurrentConvId(conv.id)
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
      >
        {renderConversationList()}
      </Drawer>

      {/* 左侧：对话列表（桌面端） */}
      {!isMobile && (
        <Card
          title="对话历史"
          style={{ width: 280, display: 'flex', flexDirection: 'column' }}
          bodyStyle={{ flex: 1, overflow: 'auto', padding: 0 }}
          extra={
            <Tooltip title="新建对话">
              <Button
                type="primary"
                icon={<PlusOutlined />}
                size="small"
                onClick={() => setCreateModalOpen(true)}
              >
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
        style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
        bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column', padding: 0 }}
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {isMobile && <MenuOutlined onClick={() => setSidebarDrawerOpen(true)} />}
            <span>Claw - 对话龙虾</span>
          </div>
        }
        extra={
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <Input
              prefix={<FolderOutlined />}
              placeholder="工作目录"
              value={workingDirectory}
              onChange={(e) => setWorkingDirectory(e.target.value)}
              style={{ width: 200 }}
              size="small"
            />
            <Select
              value={selectedModel}
              onChange={setSelectedModel}
              style={{ width: 160 }}
              size="small"
              options={models.map((m) => ({
                label: m.name,
                value: m.model_id
              }))}
            />
          </div>
        }
      >
        {/* 消息区域 */}
        <div style={{ flex: 1, overflow: 'auto', padding: 20 }}>
          {!currentConvId ? (
            <Empty description="选择或创建对话开始聊天" />
          ) : messagesLoading ? (
            <div style={{ textAlign: 'center', padding: 40 }}>
              <Spin />
            </div>
          ) : messages.length === 0 ? (
            <Empty description="暂无消息，开始对话吧" />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {messages.map((msg, index) => (
                <div
                  key={index}
                  style={{
                    display: 'flex',
                    gap: 12,
                    alignItems: 'flex-start'
                  }}
                >
                  <Avatar
                    icon={msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                    style={{
                      backgroundColor: msg.role === 'user' ? '#1890ff' : '#52c41a',
                      flexShrink: 0
                    }}
                  />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      background: msg.role === 'user' ? '#f0f0f0' : '#e6f7ff',
                      padding: '12px 16px',
                      borderRadius: 8,
                      wordBreak: 'break-word'
                    }}>
                      {msg.content || (msg.isStreaming ? <Spin size="small" /> : '(空消息)')}
                    </div>

                    {/* 工具调用卡片 */}
                    {msg.toolCalls && msg.toolCalls.length > 0 && (
                      <div style={{ marginTop: 8 }}>
                        {msg.toolCalls.map((toolCall) => (
                          <ToolCallCard key={toolCall.id} toolCall={toolCall} />
                        ))}
                      </div>
                    )}

                    {/* 子智能体卡片 */}
                    {msg.subAgents && msg.subAgents.length > 0 && (
                      <div style={{ marginTop: 8 }}>
                        {msg.subAgents.map((subAgent) => (
                          <SubAgentCard key={subAgent.id} subAgent={subAgent} />
                        ))}
                      </div>
                    )}

                    {/* 规划任务卡片 */}
                    {msg.planningTasks && msg.planningTasks.length > 0 && (
                      <div style={{ marginTop: 8 }}>
                        <PlanningCard tasks={msg.planningTasks} />
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 输入区域 */}
        <div style={{ padding: 16, borderTop: '1px solid #f0f0f0' }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <Input.TextArea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="输入消息..."
              autoSize={{ minRows: 1, maxRows: 4 }}
              disabled={!currentConvId || sending}
              onPressEnter={(e) => {
                if (!e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
            />
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSendMessage}
              disabled={!currentConvId || !inputValue.trim() || sending}
              loading={sending}
            >
              发送
            </Button>
          </div>
        </div>
      </Card>

      {/* 新建对话 Modal */}
      <Modal
        title="新建对话"
        open={createModalOpen}
        onOk={handleCreateConversation}
        onCancel={() => {
          setCreateModalOpen(false);
          createForm.resetFields();
        }}
        okText="创建"
        cancelText="取消"
      >
        <Form
          form={createForm}
          layout="vertical"
          initialValues={{
            llm_model: 'claude-opus-4-6'
          }}
        >
          <Form.Item
            label="对话标题"
            name="title"
          >
            <Input placeholder="可选，默认为'新对话'" />
          </Form.Item>
          <Form.Item
            label="工作目录"
            name="working_directory"
            rules={[{ required: true, message: '请输入工作目录' }]}
          >
            <Input
              prefix={<FolderOutlined />}
              placeholder="例如：C:\Users\YourName\Projects"
            />
          </Form.Item>
          <Form.Item
            label="LLM 模型"
            name="llm_model"
          >
            <Select
              options={models.map((m) => ({
                label: m.name,
                value: m.model_id
              }))}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ClawChatPage;