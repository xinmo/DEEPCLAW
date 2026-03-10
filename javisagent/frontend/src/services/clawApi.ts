import type {
  ClawConversation,
  ClawMessage,
  ConversationCreate,
  ConversationUpdate,
  MessageCreate,
  ModelInfo,
  SSEEvent
} from '../types/claw';

const API_BASE = '/api/claw';

export const clawApi = {
  // 对话管理
  async createConversation(data: ConversationCreate): Promise<ClawConversation> {
    const response = await fetch(`${API_BASE}/conversations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error('创建对话失败');
    return response.json();
  },

  async listConversations(): Promise<ClawConversation[]> {
    const response = await fetch(`${API_BASE}/conversations`);
    if (!response.ok) throw new Error('获取对话列表失败');
    return response.json();
  },

  async getConversation(id: string): Promise<ClawConversation> {
    const response = await fetch(`${API_BASE}/conversations/${id}`);
    if (!response.ok) throw new Error('获取对话失败');
    return response.json();
  },

  async updateConversation(id: string, data: ConversationUpdate): Promise<ClawConversation> {
    const response = await fetch(`${API_BASE}/conversations/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error('更新对话失败');
    return response.json();
  },

  async deleteConversation(id: string): Promise<void> {
    const response = await fetch(`${API_BASE}/conversations/${id}`, {
      method: 'DELETE'
    });
    if (!response.ok) throw new Error('删除对话失败');
  },

  // 消息管理
  async getMessages(convId: string): Promise<ClawMessage[]> {
    const response = await fetch(`${API_BASE}/conversations/${convId}/messages`);
    if (!response.ok) throw new Error('获取消息失败');
    return response.json();
  },

  // SSE 聊天
  async sendMessage(
    convId: string,
    message: MessageCreate,
    onEvent: (event: SSEEvent) => void,
    onError?: (error: Error) => void
  ): Promise<void> {
    const response = await fetch(`${API_BASE}/conversations/${convId}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(message)
    });

    if (!response.ok) {
      throw new Error('发送消息失败');
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      throw new Error('无法读取响应流');
    }

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              onEvent(data);
            } catch (e) {
              console.error('Failed to parse SSE data:', e);
            }
          }
        }
      }
    } catch (error) {
      if (onError) {
        onError(error as Error);
      }
      throw error;
    }
  },

  // 工具方法
  async validateDirectory(path: string): Promise<{ valid: boolean; reason?: string }> {
    const response = await fetch(`${API_BASE}/validate-directory`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path })
    });
    if (!response.ok) throw new Error('验证目录失败');
    return response.json();
  },

  async listModels(): Promise<ModelInfo[]> {
    const response = await fetch(`${API_BASE}/models`);
    if (!response.ok) throw new Error('获取模型列表失败');
    const data = await response.json();
    return data.models;
  }
};
