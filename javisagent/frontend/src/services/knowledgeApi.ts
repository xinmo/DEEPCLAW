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
  SourceInfo,
  GraphEntity,
  GraphRelationship,
  GraphStatistics,
  GraphSubgraph,
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

  async checkDocumentStatus(kbId: string, docId: string): Promise<KBDocument> {
    const res = await fetch(`${API_BASE}/kb/${kbId}/documents/${docId}/check-status`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to check document status');
    return res.json();
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

  async updateConversation(convId: string, data: { title?: string; kb_ids?: string[]; llm_model?: string }): Promise<Conversation> {
    const res = await fetch(`${API_BASE}/chat/conversations/${convId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to update conversation');
    return res.json();
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
    onSources: (sources: SourceInfo[]) => void,
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

  // ==================== 知识图谱 API ====================

  // 获取图谱统计信息
  async getGraphStatistics(kbId: string): Promise<GraphStatistics> {
    console.log(`[GraphAPI] 获取图谱统计 | kb_id=${kbId}`);
    const res = await fetch(`${API_BASE}/kb/${kbId}/graph/statistics`);
    if (!res.ok) throw new Error('Failed to fetch graph statistics');
    const data = await res.json();
    console.log(`[GraphAPI] 图谱统计结果 | 实体=${data.entity_count} | 关系=${data.relationship_count}`);
    return data;
  },

  // 获取实体列表
  async getGraphEntities(kbId: string, type?: string, limit: number = 500): Promise<GraphEntity[]> {
    console.log(`[GraphAPI] 获取实体列表 | kb_id=${kbId} | type=${type || 'all'} | limit=${limit}`);
    const params = new URLSearchParams({ limit: String(limit) });
    if (type) params.append('type', type);
    const res = await fetch(`${API_BASE}/kb/${kbId}/graph/entities?${params}`);
    if (!res.ok) throw new Error('Failed to fetch graph entities');
    const data = await res.json();
    console.log(`[GraphAPI] 获取到 ${data.length} 个实体`);
    return data;
  },

  // 获取关系列表
  async getGraphRelationships(kbId: string, limit: number = 1000): Promise<GraphRelationship[]> {
    console.log(`[GraphAPI] 获取关系列表 | kb_id=${kbId} | limit=${limit}`);
    const res = await fetch(`${API_BASE}/kb/${kbId}/graph/relationships?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch graph relationships');
    const data = await res.json();
    console.log(`[GraphAPI] 获取到 ${data.length} 个关系`);
    return data;
  },

  // 获取子图
  async getGraphSubgraph(kbId: string, entityIds: string[], maxHops: number = 1): Promise<GraphSubgraph> {
    console.log(`[GraphAPI] 获取子图 | kb_id=${kbId} | entityIds=${entityIds.join(',')} | maxHops=${maxHops}`);
    const params = new URLSearchParams({
      entity_ids: entityIds.join(','),
      max_hops: String(maxHops),
    });
    const res = await fetch(`${API_BASE}/kb/${kbId}/graph/subgraph?${params}`);
    if (!res.ok) throw new Error('Failed to fetch graph subgraph');
    const data = await res.json();
    console.log(`[GraphAPI] 子图结果 | 实体=${data.entities.length} | 关系=${data.relationships.length}`);
    return data;
  },

  // 搜索实体
  async searchGraphEntities(kbId: string, keyword: string, fuzzy: boolean = true, limit: number = 20): Promise<GraphEntity[]> {
    console.log(`[GraphAPI] 搜索实体 | kb_id=${kbId} | keyword=${keyword} | fuzzy=${fuzzy}`);
    const params = new URLSearchParams({
      keyword,
      fuzzy: String(fuzzy),
      limit: String(limit),
    });
    const res = await fetch(`${API_BASE}/kb/${kbId}/graph/search?${params}`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to search graph entities');
    const data = await res.json();
    console.log(`[GraphAPI] 搜索到 ${data.length} 个实体`);
    return data;
  },

  // 获取实体详情
  async getGraphEntityDetail(kbId: string, entityId: string, maxHops: number = 1): Promise<{
    entity: GraphEntity;
    neighbors: Array<{
      entity: { id: string; name: string; type: string; description?: string };
      relation: { type: string; direction: string; description?: string; weight?: number };
      hop: number;
    }>;
  }> {
    console.log(`[GraphAPI] 获取实体详情 | kb_id=${kbId} | entityId=${entityId} | maxHops=${maxHops}`);
    const res = await fetch(`${API_BASE}/kb/${kbId}/graph/entities/${entityId}?max_hops=${maxHops}`);
    if (!res.ok) throw new Error('Failed to fetch entity detail');
    const data = await res.json();
    console.log(`[GraphAPI] 实体详情 | name=${data.entity.name} | neighbors=${data.neighbors.length}`);
    return data;
  },
};
