import type {
  ClawMessage,
  ProcessEvent,
  ProcessStatus,
  SSEEvent,
  TimelineSnapshotEntry,
  ToolCall,
  ToolStatus,
} from "../types/claw";

export interface BubbleTimelineItem {
  id: string;
  kind: "bubble";
  role: "user" | "assistant";
  content: string;
  isStreaming: boolean;
  selectedSkill?: string;
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
  input?: unknown;
  stdout?: string;
  stderr?: string;
  exitCode?: number;
}

export interface PlanningTimelineItem {
  id: string;
  kind: "planning";
  sourceItemId: string;
  toolId?: string;
  title: string;
  status: ProcessStatus;
  todos: Array<Record<string, unknown>>;
}

export interface SubagentTimelineItem {
  id: string;
  kind: "subagent";
  toolId?: string;
  title: string;
  status: ProcessStatus;
  transcript?: string;
  result?: string;
}

export type ChatTimelineItem =
  | BubbleTimelineItem
  | ToolTimelineItem
  | ShellTimelineItem
  | PlanningTimelineItem
  | SubagentTimelineItem;

export interface TimelineState {
  items: ChatTimelineItem[];
  currentAssistantBubbleId: string | null;
  nextLocalId: number;
}

export type TimelineAction =
  | { type: "reset"; items: ChatTimelineItem[] }
  | { type: "appendUser"; content: string; selectedSkill?: string }
  | { type: "startAssistantTurn" }
  | { type: "applyEvent"; event: SSEEvent }
  | { type: "finalizeStream" };

export const initialTimelineState: TimelineState = {
  items: [],
  currentAssistantBubbleId: null,
  nextLocalId: 1,
};

const SHELL_TOOL_NAMES = new Set(["shell", "bash", "execute"]);
const PLANNING_TOOL_NAMES = new Set(["write_todos"]);
const SUBAGENT_TOOL_NAMES = new Set(["task"]);

export function mergeAdjacentAssistantBubbles(items: ChatTimelineItem[]) {
  const merged: ChatTimelineItem[] = [];

  for (const item of items) {
    const previous = merged[merged.length - 1];
    if (
      previous?.kind === "bubble" &&
      previous.role === "assistant" &&
      item.kind === "bubble" &&
      item.role === "assistant"
    ) {
      merged[merged.length - 1] = {
        ...previous,
        content: `${previous.content}${item.content}`,
        isStreaming: previous.isStreaming || item.isStreaming,
      };
      continue;
    }

    merged.push(item);
  }

  return merged;
}

function createLocalId(state: TimelineState, prefix: string) {
  return { id: `${prefix}:${state.nextLocalId}`, nextLocalId: state.nextLocalId + 1 };
}

function clearAssistantBubble(state: TimelineState): TimelineState {
  if (!state.currentAssistantBubbleId) {
    return state;
  }

  const bubbleIndex = state.items.findIndex(
    (item) => item.kind === "bubble" && item.id === state.currentAssistantBubbleId,
  );
  if (bubbleIndex === -1) {
    return { ...state, currentAssistantBubbleId: null };
  }

  const bubble = state.items[bubbleIndex];
  if (bubble.kind !== "bubble") {
    return { ...state, currentAssistantBubbleId: null };
  }

  const nextItems = [...state.items];
  if (!bubble.content.trim()) {
    nextItems.splice(bubbleIndex, 1);
  } else {
    nextItems[bubbleIndex] = { ...bubble, isStreaming: false };
  }

  return { ...state, items: nextItems, currentAssistantBubbleId: null };
}

function ensureAssistantBubble(state: TimelineState): TimelineState {
  if (state.currentAssistantBubbleId) {
    return state;
  }

  const { id, nextLocalId } = createLocalId(state, "assistant");
  const bubble: BubbleTimelineItem = {
    id,
    kind: "bubble",
    role: "assistant",
    content: "",
    isStreaming: true,
  };

  return {
    ...state,
    nextLocalId,
    currentAssistantBubbleId: id,
    items: [...state.items, bubble],
  };
}

function upsertTimelineItem(
  state: TimelineState,
  itemId: string,
  factory: () => ChatTimelineItem,
  updater: (existing: ChatTimelineItem) => ChatTimelineItem,
) {
  const index = state.items.findIndex((item) => item.id === itemId);
  if (index === -1) {
    return { ...state, items: [...state.items, factory()] };
  }

  const nextItems = [...state.items];
  nextItems[index] = updater(nextItems[index]);
  return { ...state, items: nextItems };
}

function hasTimelineItem(state: TimelineState, itemId: string, kind: ChatTimelineItem["kind"]) {
  return state.items.some((item) => item.id === itemId && item.kind === kind);
}

function isInternalToolNamespace(value?: string) {
  return typeof value === "string" && value.includes("tools:");
}

function hasInternalNamespaceValue(value: unknown): boolean {
  if (typeof value === "string") {
    return isInternalToolNamespace(value);
  }

  if (Array.isArray(value)) {
    return value.some((item) => hasInternalNamespaceValue(item));
  }

  return false;
}

function getShellCommandFromInput(input: unknown) {
  if (typeof input === "string" && input.trim()) {
    return input.trim();
  }

  if (!input || typeof input !== "object") {
    return "";
  }

  const record = input as Record<string, unknown>;

  for (const key of ["command", "cmd", "script"]) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }

  const commands = record.commands;
  if (Array.isArray(commands)) {
    const parts = commands
      .filter((value): value is string => typeof value === "string" && value.trim().length > 0)
      .map((value) => value.trim());
    if (parts.length > 0) {
      return parts.join(" && ");
    }
  }

  const args = record.args;
  if (Array.isArray(args)) {
    const parts = args
      .map((value) => String(value).trim())
      .filter(Boolean);
    if (parts.length > 0) {
      return parts.join(" ");
    }
  }

  return "";
}

function mergeToolInputs(existingInput: unknown, nextInput?: Record<string, unknown>) {
  if (!nextInput) {
    return existingInput;
  }

  if (
    typeof existingInput === "object" &&
    existingInput !== null &&
    !Array.isArray(existingInput)
  ) {
    return {
      ...(existingInput as Record<string, unknown>),
      ...nextInput,
    };
  }

  return nextInput;
}

function buildToolTimelineItem(toolCall: ToolCall): ToolTimelineItem {
  return {
    id: `tool:${toolCall.id}`,
    kind: "tool",
    toolId: toolCall.id,
    toolName: toolCall.toolName,
    status: toolCall.status,
    input: toolCall.input,
    output: toolCall.output,
    error: toolCall.error,
  };
}

function isSamePlanningTodos(
  left: Array<Record<string, unknown>>,
  right: Array<Record<string, unknown>>,
) {
  return JSON.stringify(left) === JSON.stringify(right);
}

function hasPlanningTodos(todos: Array<Record<string, unknown>> | null | undefined) {
  return Array.isArray(todos) && todos.length > 0;
}

function findLatestPlanningSnapshot(
  items: ChatTimelineItem[],
  sourceItemId: string,
) {
  for (let index = items.length - 1; index >= 0; index -= 1) {
    const item = items[index];
    if (item.kind === "planning" && item.sourceItemId === sourceItemId) {
      return item;
    }
  }

  return null;
}

function buildSpecialTimelineItem(processEvent: ProcessEvent, toolCall?: ToolCall) {
  if (processEvent.kind === "shell") {
    const data = processEvent.data || {};
    const command =
      typeof data.command === "string"
        ? data.command
        : getShellCommandFromInput(toolCall?.input);

    return {
      id: processEvent.id,
      kind: "shell" as const,
      toolId:
        typeof data.tool_id === "string"
          ? data.tool_id
          : toolCall?.id || processEvent.id.replace(/^shell:/, ""),
      title: processEvent.title,
      status: processEvent.status,
      command,
      input: data.input ?? toolCall?.input,
      stdout: typeof data.stdout === "string" ? data.stdout : undefined,
      stderr: typeof data.stderr === "string" ? data.stderr : undefined,
      exitCode: typeof data.exit_code === "number" ? data.exit_code : undefined,
    };
  }

  if (processEvent.kind === "planning") {
    const data = processEvent.data || {};
    const todos = Array.isArray(data.todos) ? (data.todos as Array<Record<string, unknown>>) : [];
    if (!hasPlanningTodos(todos)) {
      return null;
    }

    return {
      id: processEvent.id,
      kind: "planning" as const,
      sourceItemId: processEvent.id,
      toolId: typeof data.tool_id === "string" ? data.tool_id : toolCall?.id,
      title: processEvent.title,
      status: processEvent.status,
      todos,
    };
  }

  if (processEvent.kind === "subagent") {
    const data = processEvent.data || {};
    const toolId = typeof data.tool_id === "string" ? data.tool_id : toolCall?.id;
    if (!toolId && (isInternalToolNamespace(processEvent.title) || hasInternalNamespaceValue(data.namespace))) {
      return null;
    }

    return {
      id: processEvent.id,
      kind: "subagent" as const,
      toolId,
      title: processEvent.title,
      status: processEvent.status,
      transcript: typeof data.transcript === "string" ? data.transcript : undefined,
      result: typeof data.result === "string" ? data.result : undefined,
    };
  }

  return null;
}

function buildAssistantTimelineFromHistory(message: ClawMessage) {
  const timelineEntries = Array.isArray(message.metadata?.timeline)
    ? (message.metadata.timeline as TimelineSnapshotEntry[])
    : [];
  const toolCallMap = new Map((message.toolCalls || []).map((toolCall) => [toolCall.id, toolCall]));
  const processEventMap = new Map(
    (message.processEvents || []).map((processEvent) => [processEvent.id, processEvent]),
  );
  const referencedToolIds = new Set<string>();
  const referencedProcessIds = new Set<string>();
  const items: ChatTimelineItem[] = [];

  if (timelineEntries.length > 0) {
    for (const entry of timelineEntries) {
      if (entry.kind === "text" && typeof entry.content === "string") {
        items.push({
          id: entry.item_id || `${message.id}:text:${items.length + 1}`,
          kind: "bubble",
          role: "assistant",
          content: entry.content,
          isStreaming: false,
        });
        continue;
      }

      if (entry.kind === "tool" && typeof entry.tool_id === "string") {
        const toolCall = toolCallMap.get(entry.tool_id);
        if (toolCall) {
          referencedToolIds.add(toolCall.id);
          items.push(buildToolTimelineItem(toolCall));
        }
        continue;
      }

      if (
        (entry.kind === "shell" || entry.kind === "planning" || entry.kind === "subagent") &&
        typeof entry.item_id === "string"
      ) {
        const processEvent = processEventMap.get(entry.item_id);
        if (!processEvent) {
          continue;
        }

        const toolId =
          typeof processEvent.data.tool_id === "string" ? processEvent.data.tool_id : entry.tool_id;
        const toolCall = toolId ? toolCallMap.get(toolId) : undefined;
        const item = buildSpecialTimelineItem(processEvent, toolCall);
        if (item) {
          referencedProcessIds.add(processEvent.id);
          if (toolCall) {
            referencedToolIds.add(toolCall.id);
          }
          items.push(item);
        }
      }
    }
  }

  if (timelineEntries.length === 0 && message.content) {
    items.push({
      id: `history:${message.id}:assistant`,
      kind: "bubble",
      role: "assistant",
      content: message.content,
      isStreaming: false,
    });
  }

  for (const processEvent of message.processEvents || []) {
    if (referencedProcessIds.has(processEvent.id)) {
      continue;
    }
    const toolId =
      typeof processEvent.data.tool_id === "string" ? processEvent.data.tool_id : undefined;
    const item = buildSpecialTimelineItem(processEvent, toolId ? toolCallMap.get(toolId) : undefined);
    if (item) {
      referencedProcessIds.add(processEvent.id);
      if (toolId) {
        referencedToolIds.add(toolId);
      }
      items.push(item);
    }
  }

  for (const toolCall of message.toolCalls || []) {
    if (referencedToolIds.has(toolCall.id)) {
      continue;
    }
    if (
      SHELL_TOOL_NAMES.has(toolCall.toolName) ||
      PLANNING_TOOL_NAMES.has(toolCall.toolName) ||
      SUBAGENT_TOOL_NAMES.has(toolCall.toolName)
    ) {
      continue;
    }
    items.push(buildToolTimelineItem(toolCall));
  }

  return items;
}

export function buildHistoryTimeline(messages: ClawMessage[]) {
  const items: ChatTimelineItem[] = [];
  for (const message of messages) {
    if (message.role === "user") {
      items.push({
        id: `history:${message.id}:user`,
        kind: "bubble",
        role: "user",
        content: message.content,
        isStreaming: false,
        selectedSkill:
          typeof message.metadata?.selected_skill_alias === "string"
            ? message.metadata.selected_skill_alias
            : typeof message.metadata?.selected_skill === "string"
              ? message.metadata.selected_skill
            : undefined,
      });
      continue;
    }

    items.push(...buildAssistantTimelineFromHistory(message));
  }
  return mergeAdjacentAssistantBubbles(items);
}

export function timelineReducer(state: TimelineState, action: TimelineAction): TimelineState {
  if (action.type === "reset") {
    return { items: action.items, currentAssistantBubbleId: null, nextLocalId: action.items.length + 1 };
  }

  if (action.type === "appendUser") {
    const { id, nextLocalId } = createLocalId(state, "user");
    const bubble: BubbleTimelineItem = {
      id,
      kind: "bubble",
      role: "user",
      content: action.content,
      isStreaming: false,
      selectedSkill: action.selectedSkill,
    };

    return {
      ...state,
      nextLocalId,
      items: [...state.items, bubble],
    };
  }

  if (action.type === "startAssistantTurn") {
    return ensureAssistantBubble(state);
  }

  if (action.type === "finalizeStream") {
    const cleanedState = clearAssistantBubble(state);
    return {
      ...cleanedState,
      currentAssistantBubbleId: null,
      items: cleanedState.items.map((item) => item.kind === "bubble" ? { ...item, isStreaming: false } : item),
    };
  }

  if (action.event.type === "text") {
    const textEvent = action.event;
    const nextState = ensureAssistantBubble(state);
    const bubbleId = nextState.currentAssistantBubbleId;
    if (!bubbleId) {
      return nextState;
    }

    return upsertTimelineItem(
      nextState,
      bubbleId,
      () =>
        ({
          id: bubbleId,
          kind: "bubble",
          role: "assistant",
          content: textEvent.content,
          isStreaming: true,
        }) satisfies BubbleTimelineItem,
      (existing) =>
        existing.kind === "bubble"
          ? { ...existing, content: `${existing.content}${textEvent.content}`, isStreaming: true }
          : existing,
    );
  }

  const nextState = clearAssistantBubble(state);
  const { event } = action;

  if (event.type === "tool_call_started") {
    if (SHELL_TOOL_NAMES.has(event.tool_name) || PLANNING_TOOL_NAMES.has(event.tool_name) || SUBAGENT_TOOL_NAMES.has(event.tool_name)) {
      return nextState;
    }

    return upsertTimelineItem(
      nextState,
      `tool:${event.tool_id}`,
      () => ({ id: `tool:${event.tool_id}`, kind: "tool", toolId: event.tool_id, toolName: event.tool_name, status: "running", input: event.tool_input }),
      (existing) => existing.kind === "tool" ? { ...existing, toolName: event.tool_name, status: "running", input: event.tool_input } : existing,
    );
  }

  if (event.type === "tool_call_completed") {
    if (
      SHELL_TOOL_NAMES.has(event.tool_name) ||
      PLANNING_TOOL_NAMES.has(event.tool_name) ||
      SUBAGENT_TOOL_NAMES.has(event.tool_name)
    ) {
      return nextState;
    }

    return upsertTimelineItem(
      nextState,
      `tool:${event.tool_id}`,
      () => ({
        id: `tool:${event.tool_id}`,
        kind: "tool",
        toolId: event.tool_id,
        toolName: event.tool_name,
        status: event.status,
        input: event.tool_input ?? {},
        output: event.output,
        error: event.error,
      }),
      (existing) =>
        existing.kind === "tool"
          ? {
              ...existing,
              toolName: event.tool_name,
              status: event.status,
              input: mergeToolInputs(existing.input, event.tool_input),
              output: event.output,
              error: event.error,
            }
          : existing,
    );
  }

  if (event.type === "shell_started") {
    return upsertTimelineItem(
      nextState,
      event.item_id,
      () => ({
        id: event.item_id,
        kind: "shell",
        toolId: event.tool_id,
        title: event.tool_name,
        status: "running",
        command: event.command,
        input: event.tool_input,
      }),
      (existing) =>
        existing.kind === "shell"
          ? {
              ...existing,
              toolId: event.tool_id,
              title: event.tool_name,
              status: "running",
              command: event.command,
              input: event.tool_input ?? existing.input,
            }
          : existing,
    );
  }

  if (event.type === "shell_output") {
    return upsertTimelineItem(
      nextState,
      event.item_id,
      () => ({
        id: event.item_id,
        kind: "shell",
        toolId: event.tool_id,
        title: "shell",
        status: "running",
        command: event.command || "",
        stdout: event.stream === "stdout" ? event.output : undefined,
        stderr: event.stream === "stderr" ? event.output : undefined,
      }),
      (existing) => existing.kind === "shell" ? {
        ...existing,
        command: event.command || existing.command,
        stdout: event.stream === "stdout" ? `${existing.stdout || ""}${event.output}` : existing.stdout,
        stderr: event.stream === "stderr" ? `${existing.stderr || ""}${event.output}` : existing.stderr,
      } : existing,
    );
  }

  if (event.type === "shell_completed") {
    return upsertTimelineItem(
      nextState,
      event.item_id,
      () => ({
        id: event.item_id,
        kind: "shell",
        toolId: event.tool_id,
        title: "shell",
        status: event.status,
        command: event.command || "",
        input: event.tool_input,
        exitCode: event.exit_code,
      }),
      (existing) =>
        existing.kind === "shell"
          ? {
              ...existing,
              status: event.status,
              command: event.command || existing.command,
              input: event.tool_input ?? existing.input,
              exitCode: event.exit_code,
            }
          : existing,
    );
  }

  if (event.type === "planning_started") {
    if (!hasPlanningTodos(event.todos)) {
      return nextState;
    }

    return upsertTimelineItem(
      nextState,
      event.item_id,
      () => ({
        id: event.item_id,
        kind: "planning",
        sourceItemId: event.item_id,
        title: event.title,
        status: event.status,
        todos: event.todos,
      }),
      (existing) => existing.kind === "planning"
        ? {
            ...existing,
            sourceItemId: event.item_id,
            title: event.title,
            status: event.status,
            todos: event.todos,
          }
        : existing,
    );
  }

  if (event.type === "planning_updated") {
    if (!hasPlanningTodos(event.todos)) {
      return nextState;
    }

    const latestSnapshot = findLatestPlanningSnapshot(nextState.items, event.item_id);
    if (
      latestSnapshot &&
      latestSnapshot.status === event.status &&
      isSamePlanningTodos(latestSnapshot.todos, event.todos)
    ) {
      return nextState;
    }

    if (!latestSnapshot) {
      return upsertTimelineItem(
        nextState,
        event.item_id,
        () => ({
          id: event.item_id,
          kind: "planning",
          sourceItemId: event.item_id,
          title: "Planning",
          status: event.status,
          todos: event.todos,
        }),
        (existing) => existing.kind === "planning"
          ? {
              ...existing,
              sourceItemId: event.item_id,
              status: event.status,
              todos: event.todos,
            }
          : existing,
      );
    }

    const { id, nextLocalId } = createLocalId(nextState, "planning");
    return {
      ...nextState,
      nextLocalId,
      items: [
        ...nextState.items,
        {
          id,
          kind: "planning",
          sourceItemId: event.item_id,
          toolId: latestSnapshot.toolId,
          title: latestSnapshot.title,
          status: event.status,
          todos: event.todos,
        },
      ],
    };
  }

  if (event.type === "subagent_started") {
    if (isInternalToolNamespace(event.item_id) || isInternalToolNamespace(event.title)) {
      return nextState;
    }

    return upsertTimelineItem(
      nextState,
      event.item_id,
      () => ({ id: event.item_id, kind: "subagent", title: event.title, toolId: event.tool_id, status: event.status }),
      (existing) => existing.kind === "subagent" ? { ...existing, title: event.title, toolId: event.tool_id, status: event.status } : existing,
    );
  }

  if (event.type === "subagent_updated") {
    if (isInternalToolNamespace(event.item_id)) {
      return nextState;
    }

    if (!event.tool_id && !hasTimelineItem(nextState, event.item_id, "subagent")) {
      return nextState;
    }

    return upsertTimelineItem(
      nextState,
      event.item_id,
      () => ({ id: event.item_id, kind: "subagent", title: "Subagent", toolId: event.tool_id, status: event.status, transcript: event.transcript || event.delta }),
      (existing) => existing.kind === "subagent" ? {
        ...existing,
        toolId: event.tool_id ?? existing.toolId,
        status: event.status,
        transcript: event.transcript || `${existing.transcript || ""}${event.delta || ""}`,
      } : existing,
    );
  }

  if (event.type === "subagent_completed") {
    if (isInternalToolNamespace(event.item_id)) {
      return nextState;
    }

    return upsertTimelineItem(
      nextState,
      event.item_id,
      () => ({ id: event.item_id, kind: "subagent", title: "Subagent", toolId: event.tool_id, status: event.status, result: event.result }),
      (existing) => existing.kind === "subagent" ? { ...existing, toolId: event.tool_id, status: event.status, result: event.result } : existing,
    );
  }

  if (event.type === "done" || event.type === "error") {
    return timelineReducer(nextState, { type: "finalizeStream" });
  }

  return nextState;
}
