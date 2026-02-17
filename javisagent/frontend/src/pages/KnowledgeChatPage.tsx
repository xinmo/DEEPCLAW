import React, { useState, useRef, useEffect } from 'react';
import { Card, Select, Input, Button, List, Avatar, Empty, Spin, message } from 'antd';
import { SendOutlined, UserOutlined, RobotOutlined, BookOutlined } from '@ant-design/icons';
import { knowledgeApi } from '../services/knowledgeApi';
import type { KnowledgeBase, ChatMessage, ChatRequest } from '../types/knowledge';

const KnowledgeChatPage: React.FC = () => {
  const [kbs, setKBs] = useState<KnowledgeBase[]>([]);
  const [selectedKB, setSelectedKB] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [kbLoading, setKBLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadKBs();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadKBs = async () => {
    setKBLoading(true);
    try {
      const data = await knowledgeApi.listKBs();
      setKBs(data);
    } catch (e) {
      message.error('加载知识库列表失败');
    } finally {
      setKBLoading(false);
    }
  };

  const handleSend = async () => {
    if (!inputValue.trim() || !selectedKB) {
      message.warning('请选择知识库并输入问题');
      return;
    }

    const userMessage: ChatMessage = {
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setLoading(true);

    try {
      const request: ChatRequest = {
        kb_id: selectedKB,
        query: userMessage.content,
        top_k: 5,
      };
      const response = await knowledgeApi.chat(request);

      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.answer,
        sources: response.sources,
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (e) {
      message.error('获取回答失败');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div style={{ padding: 24, height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Card
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <span>知识问答</span>
            <Select
              style={{ width: 300 }}
              placeholder="请选择知识库"
              loading={kbLoading}
              value={selectedKB}
              onChange={setSelectedKB}
              options={kbs.map(kb => ({
                label: <><BookOutlined /> {kb.name}</>,
                value: kb.id,
              }))}
            />
          </div>
        }
        style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
        bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}
      >
        <div style={{ flex: 1, overflow: 'auto', marginBottom: 16 }}>
          {messages.length === 0 ? (
            <Empty description="选择知识库后开始提问" style={{ marginTop: 100 }} />
          ) : (
            <List
              dataSource={messages}
              renderItem={(msg) => (
                <List.Item style={{ border: 'none', padding: '8px 0' }}>
                  <List.Item.Meta
                    avatar={
                      <Avatar
                        icon={msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                        style={{ backgroundColor: msg.role === 'user' ? '#1890ff' : '#52c41a' }}
                      />
                    }
                    title={msg.role === 'user' ? '你' : '助手'}
                    description={
                      <div>
                        <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                        {msg.sources && msg.sources.length > 0 && (
                          <div style={{ marginTop: 8, fontSize: 12, color: '#888' }}>
                            <div>参考来源：</div>
                            {msg.sources.map((src, idx) => (
                              <div key={idx} style={{ marginLeft: 8 }}>
                                [{idx + 1}] {src.filename} (相似度: {(src.score * 100).toFixed(1)}%)
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
          {loading && (
            <div style={{ textAlign: 'center', padding: 16 }}>
              <Spin tip="思考中..." />
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div style={{ display: 'flex', gap: 8 }}>
          <Input.TextArea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="输入你的问题..."
            autoSize={{ minRows: 1, maxRows: 4 }}
            disabled={!selectedKB || loading}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            disabled={!selectedKB || !inputValue.trim() || loading}
          >
            发送
          </Button>
        </div>
      </Card>
    </div>
  );
};

export default KnowledgeChatPage;
