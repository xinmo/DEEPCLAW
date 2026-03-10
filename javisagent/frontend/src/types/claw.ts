export interface ClawConversation {
  id: string;
  title: string;
  working_directory: string;
  llm_model: string;
  created_at: string;
  updated_at: string;
}

export interface ClawMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  toolCalls?: ToolCall[];
  subAgents?: SubAgent[];
  planningTasks?: PlanningTask[];
  isStreaming?: boolean;
  timestamp: Date;
}

export interface ToolCall {
  id: string;
  toolName: string;
  status: 'running' | 'success' | 'failed';
  input: any;
  output?: any;
  duration?: number;
  error?: string;
}

export interface SubAgent {
  id: string;
  name: string;
  task: string;
  status: 'running' | 'success' | 'failed';
  progress?: number;
  result?: any;
  duration?: number;
}

export interface PlanningTask {
  id: string;
  content: string;
  status: 'pending' | 'in_progress' | 'completed';
}

export interface ConversationCreate {
  title?: string;
  working_directory: string;
  llm_model?: string;
}

export interface ConversationUpdate {
  title?: string;
  working_directory?: string;
  llm_model?: string;
}

export interface MessageCreate {
  content: string;
}

export interface ModelInfo {
  model_id: string;
  name: string;
  provider: string;
}

export interface SSEEvent {
  type: 'text' | 'tool_call' | 'tool_result' | 'subagent_start' |
        'subagent_progress' | 'subagent_complete' | 'planning' | 'done' | 'error';
  [key: string]: any;
}
