// RAG优化配置
export interface RAGConfig {
  // 切片策略: fixed(固定)/semantic(语义)/parent_child(父子文档)
  chunking_strategy: 'fixed' | 'semantic' | 'parent_child';
  // 检索策略: basic/hybrid/contextual/hyde/multi_query/graph_rag
  retrieval_strategy: 'basic' | 'hybrid' | 'contextual' | 'hyde' | 'multi_query' | 'graph_rag';
  chunk_size: number;
  chunk_overlap: number;
  // P4: 父子文档配置
  parent_chunk_size: number;
  child_chunk_size: number;
  // P3: 语义切片阈值
  semantic_threshold: number;
  // P0: 中文分词
  use_chinese_tokenizer: boolean;
  // P1: 上下文嵌入
  use_contextual_embedding: boolean;
  // P2: HyDE
  use_hyde: boolean;
  // P2: Multi-Query
  use_multi_query: boolean;
  multi_query_count: number;
  // P5: GraphRAG
  use_graph_rag: boolean;
  // GraphRAG 实体抽取使用的 LLM 模型
  graph_rag_llm_model: string;
}

// 默认RAG配置
export const DEFAULT_RAG_CONFIG: RAGConfig = {
  chunking_strategy: 'fixed',
  retrieval_strategy: 'hybrid',
  chunk_size: 500,
  chunk_overlap: 100,
  parent_chunk_size: 2000,
  child_chunk_size: 200,
  semantic_threshold: 0.5,
  use_chinese_tokenizer: true,
  use_contextual_embedding: false,
  use_hyde: false,
  use_multi_query: false,
  multi_query_count: 3,
  use_graph_rag: false,
  graph_rag_llm_model: 'gpt-4o',
};

// 知识库
export interface KnowledgeBase {
  id: string;
  name: string;
  description: string;
  icon: string;
  embedding_model: string;
  doc_count: number;
  chunk_count: number;
  rag_config?: RAGConfig;
  created_at: string;
  updated_at: string;
}

export interface KBCreateRequest {
  name: string;
  description?: string;
  icon?: string;
  embedding_model?: string;
  rag_config?: RAGConfig;
}

export interface KBUpdateRequest {
  name?: string;
  description?: string;
  icon?: string;
  rag_config?: RAGConfig;
}

// 文档处理阶段类型
export type ProcessingStage = 'uploading' | 'parsing' | 'chunking' | 'embedding' | 'storing' | 'completed' | 'failed' | '';

// 阶段显示信息
export const PROCESSING_STAGE_INFO: Record<ProcessingStage, { label: string; color: string }> = {
  'uploading': { label: '上传中', color: 'blue' },
  'parsing': { label: '解析中', color: 'blue' },
  'chunking': { label: '切片中', color: 'cyan' },
  'embedding': { label: '向量化', color: 'purple' },
  'storing': { label: '存储中', color: 'orange' },
  'completed': { label: '已完成', color: 'green' },
  'failed': { label: '失败', color: 'red' },
  '': { label: '待处理', color: 'default' },
};

// 文档
export interface KBDocument {
  id: string;
  kb_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  chunk_count: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  processing_stage: ProcessingStage;
  processing_progress: number;
  processing_message: string;
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
  index: number;
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
  { provider: 'dashscope', model_id: 'text-embedding-v4', name: '通义 Embedding V4', dimension: 2048 },
];

export const LLM_MODELS = [
  { provider: 'openai', model_id: 'gpt-4o', name: 'GPT-4o' },
  { provider: 'openai', model_id: 'gpt-4o-mini', name: 'GPT-4o Mini' },
  { provider: 'claude', model_id: 'claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet' },
  { provider: 'zhipu', model_id: 'glm-4', name: '智谱 GLM-4' },
  { provider: 'dashscope', model_id: 'qwen-max', name: '通义千问 Max' },
  { provider: 'deepseek', model_id: 'deepseek-chat', name: 'DeepSeek Chat' },
];

// ==================== 知识图谱类型 ====================

// 图谱实体
export interface GraphEntity {
  id: string;
  name: string;
  type: string;
  description: string;
  doc_id?: string;
  created_at: string;
}

// 图谱关系
export interface GraphRelationship {
  id: string;
  source_entity_id: string;
  source_name: string;
  target_entity_id: string;
  target_name: string;
  relation_type: string;
  description: string;
  weight: number;
}

// 图谱统计
export interface GraphStatistics {
  entity_count: number;
  relationship_count: number;
  entity_types: Record<string, number>;
  relationship_types: Record<string, number>;
}

// 子图
export interface GraphSubgraph {
  entities: Array<{
    id: string;
    name: string;
    type: string;
    description?: string;
  }>;
  relationships: Array<{
    source_id: string;
    source_name: string;
    target_id: string;
    target_name: string;
    relation_type: string;
    description?: string;
    weight?: number;
  }>;
}

// 实体类型颜色映射
export const ENTITY_TYPE_COLORS: Record<string, string> = {
  '人物': '#5B8FF9',
  '组织': '#5AD8A6',
  '地点': '#F6BD16',
  '概念': '#E86452',
  '事件': '#6DC8EC',
  '时间': '#945FB9',
  '作品': '#FF9845',
  '技术': '#1E9493',
  'default': '#9CA3AF',
};

// 获取实体类型颜色
export const getEntityTypeColor = (type: string): string => {
  return ENTITY_TYPE_COLORS[type] || ENTITY_TYPE_COLORS['default'];
};
