// 知识库
export interface KnowledgeBase {
  id: string;
  name: string;
  description: string;
  icon: string;
  embedding_model: string;
  doc_count: number;
  chunk_count: number;
  created_at: string;
  updated_at: string;
}

export interface KBCreateRequest {
  name: string;
  description?: string;
  icon?: string;
  embedding_model?: string;
}

export interface KBUpdateRequest {
  name?: string;
  description?: string;
  icon?: string;
}

// 文档
export interface KBDocument {
  id: string;
  kb_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  chunk_count: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  error_msg: string;
  created_at: string;
}

// 对话
export interface Conversation {
  id: string;
  kb_ids: string[];
  title: string;
  llm_model: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationCreateRequest {
  kb_ids: string[];
  title?: string;
  llm_model?: string;
}

// 消息
export interface SourceInfo {
  doc_id: string;
  filename: string;
  text: string;
  score: number;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  sources: SourceInfo[];
  created_at: string;
}

export interface MessageCreateRequest {
  content: string;
}

// SSE 事件类型
export interface SSEChunkEvent {
  type: 'chunk';
  content: string;
}

export interface SSESourcesEvent {
  type: 'sources';
  sources: SourceInfo[];
}

export interface SSEDoneEvent {
  type: 'done';
}

export type SSEEvent = SSEChunkEvent | SSESourcesEvent | SSEDoneEvent;

// 模型配置
export interface ModelConfig {
  id: string;
  type: 'embedding' | 'llm';
  provider: string;
  name: string;
  model_id: string;
  base_url: string;
  is_default: boolean;
  created_at: string;
}

// 可用模型选项
export const EMBEDDING_MODELS = [
  { provider: 'openai', model_id: 'text-embedding-3-small', name: 'OpenAI Embedding Small' },
  { provider: 'openai', model_id: 'text-embedding-3-large', name: 'OpenAI Embedding Large' },
  { provider: 'zhipu', model_id: 'embedding-2', name: '智谱 Embedding-2' },
  { provider: 'dashscope', model_id: 'text-embedding-v2', name: '通义 Embedding V2' },
];

export const LLM_MODELS = [
  { provider: 'openai', model_id: 'gpt-4o', name: 'GPT-4o' },
  { provider: 'openai', model_id: 'gpt-4o-mini', name: 'GPT-4o Mini' },
  { provider: 'claude', model_id: 'claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet' },
  { provider: 'zhipu', model_id: 'glm-4', name: '智谱 GLM-4' },
  { provider: 'dashscope', model_id: 'qwen-max', name: '通义千问 Max' },
  { provider: 'deepseek', model_id: 'deepseek-chat', name: 'DeepSeek Chat' },
];
