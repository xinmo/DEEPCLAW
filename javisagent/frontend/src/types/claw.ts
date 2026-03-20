export interface TextContentBlock {
  type: "text";
  text: string;
}

export interface ImageContentBlock {
  type: "image_url";
  image_url: { url: string }; // data:image/xxx;base64,...
}

export type ContentBlock = TextContentBlock | ImageContentBlock;

export interface ClawConversation {
  id: string;
  title: string;
  working_directory: string;
  llm_model: string;
  created_at: string;
  updated_at: string;
}

export type ClawRole = "user" | "assistant";
export type ToolStatus = "running" | "success" | "failed";
export type ProcessStatus =
  | "pending"
  | "running"
  | "in_progress"
  | "completed"
  | "success"
  | "failed";
export type ProcessKind = "tool" | "shell" | "planning" | "subagent";
export type TimelineSnapshotKind = "text" | "tool" | "shell" | "planning" | "subagent";

export interface TimelineSnapshotEntry {
  kind: TimelineSnapshotKind;
  item_id?: string;
  tool_id?: string;
  content?: string;
}

export interface PromptDebugLayer {
  id: string;
  title: string;
  source: string;
  content: string;
}

export interface PromptDebugMessage {
  role: string;
  type: string;
  name?: string | null;
  content?: unknown;
  content_text?: string;
  additional_kwargs?: Record<string, unknown> | null;
  tool_calls?: unknown;
}

export interface PromptDebugTool {
  name: string;
  description: string;
  input_schema?: unknown;
}

export interface PromptDebugSkillSummary {
  name: string;
  declared_name?: string;
  description?: string;
  aliases?: string[];
  path?: string;
}

export interface PromptDebugSnapshot {
  version: string;
  captured_at?: string;
  conversation: {
    id: string;
    llm_model: string;
    working_directory: string;
  };
  selected_skill?: PromptDebugSkillSummary | null;
  prompt_layers: PromptDebugLayer[];
  captured_request: {
    system_prompt: string;
    message_count: number;
    messages: PromptDebugMessage[];
    tool_count: number;
    tools: PromptDebugTool[];
  };
  resolved_state: {
    local_context?: string;
    memory_contents?: Record<string, string>;
    skills_source_paths?: string[];
    skills_loaded?: Array<Record<string, unknown>>;
    summarization_event?: Record<string, unknown> | null;
  };
}

export interface ClawMessageMetadata extends Record<string, unknown> {
  stream_protocol?: string;
  tool_call_count?: number;
  process_event_count?: number;
  timeline?: TimelineSnapshotEntry[];
  prompt_debug?: PromptDebugSnapshot;
  selected_skill?: string | null;
  selected_skill_alias?: string | null;
}

export interface ToolCall {
  id: string;
  toolName: string;
  status: ToolStatus;
  input: unknown;
  output?: unknown;
  duration?: number;
  error?: string;
}

export interface SubagentChildTool {
  id: string;
  tool_name: string;
  status: ToolStatus;
  tool_input?: unknown;
  tool_output?: unknown;
  error?: string;
}

export interface ProcessEvent {
  id: string;
  kind: ProcessKind;
  title: string;
  status: ProcessStatus;
  sequence: number;
  data: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ClawMessage {
  id: string;
  role: ClawRole;
  content: string;
  metadata?: ClawMessageMetadata;
  toolCalls?: ToolCall[];
  processEvents?: ProcessEvent[];
  isStreaming?: boolean;
  timestamp: Date;
}

export interface TextTimelineItem {
  id: string;
  kind: "text";
  role: "assistant";
  content: string;
}

export interface ToolTimelineItem {
  id: string;
  kind: "tool";
  toolId: string;
  toolName: string;
  status: ToolStatus;
  input: unknown;
  output?: unknown;
  error?: string;
}

export interface ShellTimelineItem {
  id: string;
  kind: "shell";
  toolId: string;
  title: string;
  status: ProcessStatus;
  command: string;
  stdout?: string;
  stderr?: string;
  exitCode?: number;
}

export interface PlanningTimelineItem {
  id: string;
  kind: "planning";
  title: string;
  status: ProcessStatus;
  todos: Array<Record<string, unknown>>;
}

export interface SubAgentTimelineItem {
  id: string;
  kind: "subagent";
  title: string;
  status: ProcessStatus;
  toolId?: string;
  transcript?: string;
  result?: string;
  childTools?: ToolCall[];
}

export type TimelineItem =
  | TextTimelineItem
  | ToolTimelineItem
  | ShellTimelineItem
  | PlanningTimelineItem
  | SubAgentTimelineItem;

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
  content: string | ContentBlock[];
  selected_skill?: string | null;
}

export interface ModelInfo {
  model_id: string;
  name: string;
  provider: string;
}

export interface ClawSkillSummary {
  name: string;
  declared_name?: string | null;
  description: string;
  enabled: boolean;
  aliases: string[];
  path: string;
  skill_file_path: string;
  updated_at: string;
  version?: string | null;
}

export interface ClawSkillDetail extends ClawSkillSummary {
  compatibility?: string | null;
  license?: string | null;
  allowed_tools: string[];
  metadata: Record<string, string>;
  content: string;
}

export interface ClawSkillsStats {
  total: number;
  enabled: number;
  disabled: number;
}

export interface MCPServerConfig {
  type?: string;
  command?: string;
  args?: string[];
  url?: string;
  headers?: Record<string, string>;
  env?: Record<string, string>;
  [key: string]: unknown;
}

export interface MCPConfig {
  mcpServers: Record<string, MCPServerConfig>;
}

export interface TextChunkEvent {
  type: "text";
  message_id?: string;
  content: string;
}

export interface ToolCallStartedEvent {
  type: "tool_call_started";
  tool_id: string;
  tool_name: string;
  tool_input: Record<string, unknown>;
}

export interface ToolCallDeltaEvent {
  type: "tool_call_delta";
  tool_id: string;
  tool_name?: string;
  delta: string;
}

export interface ToolCallCompletedEvent {
  type: "tool_call_completed";
  tool_id: string;
  tool_name: string;
  tool_input?: Record<string, unknown>;
  status: Exclude<ToolStatus, "running">;
  output?: unknown;
  error?: string;
}

export interface ShellStartedEvent {
  type: "shell_started";
  item_id: string;
  tool_id: string;
  tool_name: string;
  command: string;
  tool_input?: Record<string, unknown>;
}

export interface ShellOutputEvent {
  type: "shell_output";
  item_id: string;
  tool_id: string;
  stream: "stdout" | "stderr";
  output: string;
  command?: string;
}

export interface ShellCompletedEvent {
  type: "shell_completed";
  item_id: string;
  tool_id: string;
  status: Exclude<ProcessStatus, "pending" | "running">;
  exit_code?: number;
  command?: string;
  tool_input?: Record<string, unknown>;
  output?: unknown;
  error?: string;
}

export interface PlanningStartedEvent {
  type: "planning_started";
  item_id: string;
  title: string;
  status: ProcessStatus;
  todos: Array<Record<string, unknown>>;
}

export interface PlanningUpdatedEvent {
  type: "planning_updated";
  item_id: string;
  status: ProcessStatus;
  todos: Array<Record<string, unknown>>;
}

export interface SubagentStartedEvent {
  type: "subagent_started";
  item_id: string;
  title: string;
  tool_id?: string;
  status: ProcessStatus;
}

export interface SubagentUpdatedEvent {
  type: "subagent_updated";
  item_id: string;
  tool_id?: string;
  status: ProcessStatus;
  delta?: string;
  transcript?: string;
  state?: Record<string, unknown>;
  child_tools?: SubagentChildTool[];
}

export interface SubagentCompletedEvent {
  type: "subagent_completed";
  item_id: string;
  tool_id: string;
  status: Exclude<ProcessStatus, "pending" | "running">;
  result?: string;
  child_tools?: SubagentChildTool[];
}

export interface DoneEvent {
  type: "done";
}

export interface ErrorEvent {
  type: "error";
  message: string;
}

export interface PromptDebugEvent {
  type: "prompt_debug";
  user_message_id: string;
  prompt_debug: PromptDebugSnapshot;
}

export type SSEEvent =
  | TextChunkEvent
  | ToolCallStartedEvent
  | ToolCallDeltaEvent
  | ToolCallCompletedEvent
  | ShellStartedEvent
  | ShellOutputEvent
  | ShellCompletedEvent
  | PlanningStartedEvent
  | PlanningUpdatedEvent
  | SubagentStartedEvent
  | SubagentUpdatedEvent
  | SubagentCompletedEvent
  | PromptDebugEvent
  | DoneEvent
  | ErrorEvent;
