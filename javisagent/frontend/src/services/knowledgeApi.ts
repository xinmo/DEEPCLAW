import type {
  KnowledgeBase,
  KBCreateRequest,
  KBUpdateRequest,
  KBDocument,
  Conversation,
  ConversationCreateRequest,
  Message,
  MessageCreateRequest,
  SSEEvent,
} from '../types/knowledge';

const API_BASE = '/api';

// 知识库 API
export const knowledgeApi = {
  // 知识库 CRUD
  async listKBs(): Promise<KnowledgeBase[]> {
    const res = await fetch(`${API_BASE}/kb`);
    if (!res.ok) throw new Error('Failed to fetch knowledge bases');
    return res.json();
  },

  async getKB(kbId: string): Promise<KnowledgeBase> {
    const res = await fetch(`${API_BASE}/kb/${kbId}`);
    if (!res.ok) throw new Error('Failed to fetch knowledge base');
    return res.json();
  },

  async createKB(data: KBCreateRequest): Promise<KnowledgeBase> {
    const res = await fetch(`${API_BASE}/kb`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to create knowledge base');
    return res.json();
  },

  async updateKB(kbId: string, data: KBUpdateRequest): Promise<KnowledgeBase> {
    const res = await fetch(`${API_BASE}/kb/${kbId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to update knowledge base');
    return res.json();
  },

  async deleteKB(kbId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/kb/${kbId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete knowledge base');
  },

  // 文档 API
  async listDocuments(kbId: string): Promise<KBDocument[]> {
    const res = await fetch(`${API_BASE}/kb/${kbId}/documents`);
    if (!res.ok) throw new Error('Failed to fetch documents');
    return res.json();
  },

  async uploadDocument(kbId: string, file: File): Promise<KBDocument> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/kb/${kbId}/documents`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) throw new Error('Failed to upload document');
    return res.json();
  },

  async deleteDocument(kbId: string, docId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/kb/${kbId}/documents/${docId}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete document');
  },

  // 对话 API
  async listConversations(): Promise<Conversation[]> {
    const res = await fetch(`${API_BASE}/chat/conversations`);
    if (!res.ok) throw new Error('Failed to fetch conversations');
    return res.json();
  },

  async getConversation(convId: string): Promise<Conversation> {
    const res = await fetch(`${API_BASE}/chat/conversations/${convId}`);
    if (!res.ok) throw new Error('Failed to fetch conversation');
    return res.json();
  },

  async createConversation(data: ConversationCreateRequest): Promise<Conversation> {
    const res = await fetch(`${API_BASE}/chat/conversations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to create conversation');
    return res.json();
  },

  async deleteConversation(convId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/chat/conversations/${convId}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete conversation');
  },

  async getMessages(convId: string): Promise<Message[]> {
    const res = await fetch(`${API_BASE}/chat/conversations/${convId}/messages`);
    if (!res.ok) throw new Error('Failed to fetch messages');
    return res.json();
  },

  // 发送消息（SSE 流式）
  async sendMessage(
    convId: string,
    data: MessageCreateRequest,
    onChunk: (content: string) => void,
    onSources: (sources: SSEEvent['sources']) => void,
    onDone: () => void
  ): Promise<void> {
    const res = await fetch(`${API_BASE}/chat/conversations/${convId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });

    if (!res.ok) throw new Error('Failed to send message');
    if (!res.body) throw new Error('No response body');

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event: SSEEvent = JSON.parse(line.slice(6));
            if (event.type === 'chunk') {
              onChunk(event.content);
            } else if (event.type === 'sources') {
              onSources(event.sources);
            } else if (event.type === 'done') {
              onDone();
            }
          } catch (e) {
            console.error('Failed to parse SSE event:', e);
          }
        }
      }
    }
  },
};
