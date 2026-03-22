import type {
  ClawConversation,
  ClawSkillDetail,
  ClawSkillsStats,
  ClawSkillSummary,
  ClawMessage,
  ClawMessageMetadata,
  ConversationCreate,
  ConversationUpdate,
  MCPConfig,
  MessageCreate,
  ModelInfo,
  ProcessEvent,
  SSEEvent,
  ToolCall,
} from "../types/claw";

const API_BASE = "/api/claw";

interface RawToolCall {
  id: string;
  tool_name: string;
  tool_input: unknown;
  tool_output?: unknown;
  status: "running" | "success" | "failed";
  duration?: number;
  error?: string;
}

interface RawProcessEvent {
  id: string;
  kind: ProcessEvent["kind"];
  title: string;
  status: ProcessEvent["status"];
  sequence: number;
  data: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

interface RawClawMessage {
  id: string;
  role: ClawMessage["role"];
  content: string;
  metadata?: ClawMessageMetadata;
  tool_calls?: RawToolCall[];
  process_events?: RawProcessEvent[];
  created_at: string;
}

function normalizeToolCall(raw: RawToolCall): ToolCall {
  return {
    id: raw.id,
    toolName: raw.tool_name,
    status: raw.status,
    input: raw.tool_input,
    output: raw.tool_output,
    duration: raw.duration,
    error: raw.error,
  };
}

function normalizeProcessEvent(raw: RawProcessEvent): ProcessEvent {
  return {
    id: raw.id,
    kind: raw.kind,
    title: raw.title,
    status: raw.status,
    sequence: raw.sequence,
    data: raw.data || {},
    created_at: raw.created_at,
    updated_at: raw.updated_at,
  };
}

function normalizeMessage(raw: RawClawMessage): ClawMessage {
  return {
    id: raw.id,
    role: raw.role,
    content: raw.content,
    metadata: raw.metadata || {},
    toolCalls: (raw.tool_calls || []).map(normalizeToolCall),
    processEvents: (raw.process_events || []).map(normalizeProcessEvent),
    isStreaming: false,
    timestamp: new Date(raw.created_at),
  };
}

async function expectJson<T>(response: Response, errorMessage: string): Promise<T> {
  if (!response.ok) {
    try {
      const errBody = await response.json() as { detail?: string };
      const detail = errBody?.detail;
      throw new Error(typeof detail === "string" ? detail : errorMessage);
    } catch (e) {
      if (e instanceof SyntaxError) throw new Error(errorMessage);
      throw e;
    }
  }
  return response.json() as Promise<T>;
}

function parseSseChunk(chunk: string, onEvent: (event: SSEEvent) => void) {
  const eventBlocks = chunk.split("\n\n");
  const incomplete = eventBlocks.pop() ?? "";

  for (const block of eventBlocks) {
    const dataLines = block
      .split("\n")
      .filter((line) => line.startsWith("data: "))
      .map((line) => line.slice(6));

    if (dataLines.length === 0) {
      continue;
    }

    try {
      const payload = JSON.parse(dataLines.join("\n")) as SSEEvent;
      onEvent(payload);
    } catch (error) {
      console.error("[Claw SSE] Failed to parse event block", error, block);
    }
  }

  return incomplete;
}

export function isAbortLikeError(error: unknown) {
  if (!error) {
    return false;
  }

  if (error instanceof DOMException && error.name === "AbortError") {
    return true;
  }

  const normalizedMessage =
    error instanceof Error
      ? `${error.name} ${error.message}`.toLowerCase()
      : String(error).toLowerCase();

  return (
    normalizedMessage.includes("aborterror") ||
    normalizedMessage.includes("was aborted") ||
    normalizedMessage.includes("signal is aborted") ||
    normalizedMessage.includes("stream was cancelled")
  );
}

export const clawApi = {
  async createConversation(data: ConversationCreate): Promise<ClawConversation> {
    const response = await fetch(`${API_BASE}/conversations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    return expectJson<ClawConversation>(response, "创建对话失败");
  },

  async listConversations(): Promise<ClawConversation[]> {
    const response = await fetch(`${API_BASE}/conversations`);
    return expectJson<ClawConversation[]>(response, "获取对话列表失败");
  },

  async getConversation(id: string): Promise<ClawConversation> {
    const response = await fetch(`${API_BASE}/conversations/${id}`);
    return expectJson<ClawConversation>(response, "获取对话失败");
  },

  async updateConversation(
    id: string,
    data: ConversationUpdate,
  ): Promise<ClawConversation> {
    const response = await fetch(`${API_BASE}/conversations/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    return expectJson<ClawConversation>(response, "更新对话失败");
  },

  async deleteConversation(id: string): Promise<void> {
    const response = await fetch(`${API_BASE}/conversations/${id}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      throw new Error("删除对话失败");
    }
  },

  async getMessages(convId: string): Promise<ClawMessage[]> {
    const response = await fetch(`${API_BASE}/conversations/${convId}/messages`);
    const rawMessages = await expectJson<RawClawMessage[]>(response, "获取消息失败");
    return rawMessages.map(normalizeMessage);
  },

  async sendMessage(
    convId: string,
    message: MessageCreate,
    onEvent: (event: SSEEvent) => void,
    onError?: (error: Error) => void,
    signal?: AbortSignal,
  ): Promise<void> {
    const response = await fetch(`${API_BASE}/conversations/${convId}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(message),
      signal,
    });

    if (!response.ok) {
      throw new Error("发送消息失败");
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error("无法读取响应流");
    }

    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        buffer = parseSseChunk(buffer, onEvent);
      }

      const finalChunk = decoder.decode();
      if (finalChunk) {
        buffer += finalChunk;
      }

      if (buffer.trim()) {
        parseSseChunk(`${buffer}\n\n`, onEvent);
      }
    } catch (error) {
      const eventError = error instanceof Error ? error : new Error(String(error));
      onError?.(eventError);
      throw eventError;
    } finally {
      reader.releaseLock();
    }
  },

  async validateDirectory(
    path: string,
  ): Promise<{ valid: boolean; reason?: string }> {
    const response = await fetch(`${API_BASE}/validate-directory`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path }),
    });
    return expectJson<{ valid: boolean; reason?: string }>(
      response,
      "验证目录失败",
    );
  },

  async listModels(): Promise<ModelInfo[]> {
    const response = await fetch(`${API_BASE}/models`);
    const data = await expectJson<{ models: ModelInfo[] }>(response, "获取模型列表失败");
    return data.models;
  },

  async listSkills(): Promise<{ skills: ClawSkillSummary[]; stats: ClawSkillsStats }> {
    const response = await fetch(`${API_BASE}/skills`);
    return expectJson<{ skills: ClawSkillSummary[]; stats: ClawSkillsStats }>(
      response,
      "Failed to load skills",
    );
  },

  async getSkillDetail(name: string): Promise<ClawSkillDetail> {
    const response = await fetch(`${API_BASE}/skills/${encodeURIComponent(name)}`);
    return expectJson<ClawSkillDetail>(response, "Failed to load skill detail");
  },

  async updateSkillStatus(
    name: string,
    enabled: boolean,
  ): Promise<{ success: boolean; skill: ClawSkillSummary }> {
    const response = await fetch(`${API_BASE}/skills/${encodeURIComponent(name)}/status`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    });
    return expectJson<{ success: boolean; skill: ClawSkillSummary }>(
      response,
      "Failed to update skill status",
    );
  },

  async getMcpConfig(): Promise<MCPConfig> {
    const response = await fetch(`${API_BASE}/mcp`);
    return expectJson<MCPConfig>(response, "获取 MCP 配置失败");
  },

  async saveMcpConfig(config: MCPConfig): Promise<{ success: boolean; mcpServers: MCPConfig["mcpServers"] }> {
    const response = await fetch(`${API_BASE}/mcp`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });
    return expectJson<{ success: boolean; mcpServers: MCPConfig["mcpServers"] }>(
      response,
      "保存 MCP 配置失败",
    );
  },
};
