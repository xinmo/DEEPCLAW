import React, { useCallback, useDeferredValue, useEffect, useRef, useState } from "react";
import {
  Avatar,
  Button,
  Card,
  Drawer,
  Empty,
  Form,
  Input,
  Menu,
  Modal,
  Popconfirm,
  Select,
  Spin,
  Tag,
  Tooltip,
  message,
} from "antd";
import {
  ArrowDownOutlined,
  CloseCircleOutlined,
  DeleteOutlined,
  FolderOutlined,
  MenuOutlined,
  MessageOutlined,
  PlusOutlined,
  SearchOutlined,
  SendOutlined,
  UserOutlined,
} from "@ant-design/icons";
import ReactMarkdown from "react-markdown";

import DirectoryBrowser from "../components/Claw/DirectoryBrowser";
import PlanningCard from "../components/Claw/PlanningCard";
import PromptDebugPanel from "../components/Claw/PromptDebugPanel";
import ShellExecutionCard from "../components/Claw/ShellExecutionCard";
import SubAgentCard from "../components/Claw/SubAgentCard";
import ToolCallCard from "../components/Claw/ToolCallCard";
import { dispatchClawStreamStatus } from "../constants/clawChat";
import { clawApi, isAbortLikeError } from "../services/clawApi";
import type { ClawConversation, ClawSkillSummary, ContentBlock, ModelInfo } from "../types/claw";
import {
  buildHistoryTimeline,
  initialTimelineState,
  mergeAdjacentAssistantBubbles,
  timelineReducer,
  type ChatTimelineItem,
  type TimelineAction,
  type TimelineState,
} from "./clawTimeline";

const BOTTOM_LOCK_THRESHOLD = 96;
const CHAT_VIEWPORT_HEIGHT = "calc(100vh - 96px)";
const RESERVED_SLASH_COMMANDS = new Set([
  "help",
  "clear",
  "compact",
  "mcp",
  "model",
  "reload",
  "remember",
  "tokens",
  "threads",
  "trace",
  "changelog",
  "docs",
  "feedback",
  "version",
  "quit",
  "q",
]);

function normalizeSkillReference(value: string | null | undefined) {
  if (!value) {
    return "";
  }
  return value.trim().toLowerCase().replace(/^\/+/, "");
}

function getPreferredSkillAlias(skill: ClawSkillSummary) {
  const aliases = Array.isArray(skill.aliases) ? skill.aliases : [];
  return aliases[0] || normalizeSkillReference(skill.declared_name) || normalizeSkillReference(skill.name) || skill.name;
}

function getSlashDraft(value: string) {
  const trimmedValue = value.trim();
  if (!trimmedValue.startsWith("/") || trimmedValue.startsWith("//") || trimmedValue.includes("\n")) {
    return null;
  }

  const withoutSlash = trimmedValue.slice(1);
  const whitespaceIndex = withoutSlash.search(/\s/);
  const query = whitespaceIndex === -1 ? withoutSlash : withoutSlash.slice(0, whitespaceIndex);
  const remainder = whitespaceIndex === -1 ? "" : withoutSlash.slice(whitespaceIndex).trimStart();
  return {
    query: normalizeSkillReference(query),
    remainder,
  };
}

function findExactSkillMatches(skills: ClawSkillSummary[], reference: string) {
  const normalizedReference = normalizeSkillReference(reference);
  if (!normalizedReference || RESERVED_SLASH_COMMANDS.has(normalizedReference)) {
    return [];
  }

  const exactNameMatches = skills.filter(
    (skill) => normalizeSkillReference(skill.name) === normalizedReference,
  );
  if (exactNameMatches.length > 0) {
    return exactNameMatches;
  }

  const exactDeclaredMatches = skills.filter(
    (skill) => normalizeSkillReference(skill.declared_name) === normalizedReference,
  );
  if (exactDeclaredMatches.length > 0) {
    return exactDeclaredMatches;
  }

  return skills.filter((skill) => {
    const aliases = Array.isArray(skill.aliases) ? skill.aliases : [];
    return aliases.includes(normalizedReference);
  });
}

interface ClawChatPageProps {
  active?: boolean;
}

interface ConversationSessionState {
  timeline: TimelineState;
  messagesLoading: boolean;
  sending: boolean;
  hasLoadedHistory: boolean;
}

function createInitialConversationSessionState(): ConversationSessionState {
  return {
    timeline: {
      ...initialTimelineState,
      items: [...initialTimelineState.items],
    },
    messagesLoading: false,
    sending: false,
    hasLoadedHistory: false,
  };
}

const EMPTY_CONVERSATION_SESSION = createInitialConversationSessionState();

function readFileAsDataURL(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

const ClawChatPage: React.FC<ClawChatPageProps> = ({ active = true }) => {
  const [conversations, setConversations] = useState<ClawConversation[]>([]);
  const [currentConvId, setCurrentConvId] = useState<string | null>(() =>
    localStorage.getItem("claw_chat_conv_id"),
  );
  const [convLoading, setConvLoading] = useState(false);
  const [conversationSessions, setConversationSessions] = useState<
    Record<string, ConversationSessionState>
  >({});
  const [inputValue, setInputValue] = useState("");
  const [attachedImages, setAttachedImages] = useState<string[]>([]);
  const [availableSkills, setAvailableSkills] = useState<ClawSkillSummary[]>([]);
  const [selectedSkill, setSelectedSkill] = useState<ClawSkillSummary | null>(null);
  const [workingDirectory, setWorkingDirectory] = useState("");
  const [selectedModel, setSelectedModel] = useState("deepseek-chat");
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [searchKeyword, setSearchKeyword] = useState("");
  const deferredSearchKeyword = useDeferredValue(searchKeyword);
  const [sidebarDrawerOpen, setSidebarDrawerOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [directoryBrowserOpen, setDirectoryBrowserOpen] = useState(false);
  const [isPinnedToBottom, setIsPinnedToBottom] = useState(true);
  const [pendingMessageCount, setPendingMessageCount] = useState(0);
  const [createForm] = Form.useForm();
  const timelineContainerRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const activeRequestControllersRef = useRef<Record<string, AbortController | null>>({});
  const abortRequestedRef = useRef<Record<string, boolean>>({});
  const shouldSnapToBottomRef = useRef(true);
  const lastSeenItemCountRef = useRef(0);

  const currentConversation =
    conversations.find((conversation) => conversation.id === currentConvId) || null;
  const currentSession = currentConvId
    ? conversationSessions[currentConvId] || EMPTY_CONVERSATION_SESSION
    : null;
  const timelineState = currentSession?.timeline || EMPTY_CONVERSATION_SESSION.timeline;
  const messagesLoading = currentSession?.messagesLoading ?? false;
  const sending = currentSession?.sending ?? false;
  const displayTimelineItems = mergeAdjacentAssistantBubbles(timelineState.items);
  const timelineItemCount = displayTimelineItems.length;
  const filteredConversations = conversations.filter((conversation) =>
    conversation.title.toLowerCase().includes(deferredSearchKeyword.toLowerCase()),
  );
  const slashDraft = selectedSkill ? null : getSlashDraft(inputValue);
  const slashSuggestions =
    slashDraft && !slashDraft.remainder
      ? availableSkills
          .filter((skill) => {
            if (!slashDraft.query) {
              return true;
            }
            const prefix = slashDraft.query;
            return (
              normalizeSkillReference(skill.name).startsWith(prefix) ||
              normalizeSkillReference(skill.declared_name).startsWith(prefix) ||
              (Array.isArray(skill.aliases) ? skill.aliases : []).some((alias) => alias.startsWith(prefix))
            );
          })
          .slice(0, 8)
      : [];

  const updateConversationSession = useCallback(
    (
      conversationId: string,
      updater: (session: ConversationSessionState) => ConversationSessionState,
    ) => {
      setConversationSessions((current) => {
        const session = current[conversationId] || createInitialConversationSessionState();
        const nextSession = updater(session);
        if (nextSession === session) {
          return current;
        }
        return {
          ...current,
          [conversationId]: nextSession,
        };
      });
    },
    [],
  );

  const applyTimelineAction = useCallback(
    (conversationId: string, action: TimelineAction) => {
      updateConversationSession(conversationId, (session) => {
        const nextTimeline = timelineReducer(session.timeline, action);
        if (nextTimeline === session.timeline) {
          return session;
        }
        return {
          ...session,
          timeline: nextTimeline,
        };
      });
    },
    [updateConversationSession],
  );

  const clearConversationSession = useCallback((conversationId: string) => {
    activeRequestControllersRef.current[conversationId]?.abort();
    delete activeRequestControllersRef.current[conversationId];
    delete abortRequestedRef.current[conversationId];

    setConversationSessions((current) => {
      if (!(conversationId in current)) {
        return current;
      }

      const nextSessions = { ...current };
      delete nextSessions[conversationId];
      return nextSessions;
    });
  }, []);

  const loadConversations = useCallback(async () => {
    setConvLoading(true);
    try {
      setConversations(await clawApi.listConversations());
    } catch {
      message.error("加载对话列表失败");
    } finally {
      setConvLoading(false);
    }
  }, []);

  const loadModels = useCallback(async () => {
    try {
      setModels(await clawApi.listModels());
    } catch {
      message.error("加载模型列表失败");
    }
  }, []);

  const loadSkills = useCallback(async () => {
    try {
      const data = await clawApi.listSkills();
      setAvailableSkills(data.skills.filter((skill) => skill.enabled));
      setSelectedSkill((current) => {
        if (!current) {
          return current;
        }
        return data.skills.find((skill) => skill.enabled && skill.name === current.name) || null;
      });
    } catch (error) {
      console.error("Failed to load skills for slash suggestions", error);
    }
  }, []);

  const handleImageFiles = useCallback(async (files: FileList | File[]) => {
    const fileArray = Array.from(files).filter((f) => f.type.startsWith("image/"));
    if (fileArray.length === 0) return;

    const remaining = 4 - attachedImages.length;
    if (remaining <= 0) {
      message.warning("最多上传 4 张图片");
      return;
    }

    const toProcess = fileArray.slice(0, remaining);
    const oversized = toProcess.filter((f) => f.size > 10 * 1024 * 1024);
    if (oversized.length > 0) {
      message.error(`图片大小不能超过 10MB（${oversized.map((f) => f.name).join(", ")}）`);
      return;
    }

    try {
      const dataUrls = await Promise.all(toProcess.map(readFileAsDataURL));
      setAttachedImages((prev) => [...prev, ...dataUrls].slice(0, 4));
    } catch {
      message.error("图片读取失败");
    }
  }, [attachedImages.length]);

  const handlePaste = useCallback(
    (e: React.ClipboardEvent) => {
      const items = Array.from(e.clipboardData.items);
      const imageItems = items.filter((item) => item.type.startsWith("image/"));
      if (imageItems.length === 0) return;
      e.preventDefault();
      const files = imageItems
        .map((item) => item.getAsFile())
        .filter((f): f is File => f !== null);
      void handleImageFiles(files);
    },
    [handleImageFiles],
  );

  useEffect(() => {
    void loadConversations();
    void loadModels();
    void loadSkills();
  }, [loadConversations, loadModels, loadSkills]);

  useEffect(() => {
    if (currentConvId) {
      localStorage.setItem("claw_chat_conv_id", currentConvId);
    } else {
      localStorage.removeItem("claw_chat_conv_id");
    }
  }, [currentConvId]);

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  useEffect(() => {
    if (currentConversation) {
      setWorkingDirectory(currentConversation.working_directory);
      setSelectedModel(currentConversation.llm_model);
    } else {
      setWorkingDirectory("");
      setSelectedModel("deepseek-chat");
    }
  }, [currentConversation]);

  useEffect(() => {
    const activeStreamConversationId =
      (currentConvId && conversationSessions[currentConvId]?.sending ? currentConvId : null) ||
      Object.entries(conversationSessions).find(([, session]) => session.sending)?.[0] ||
      null;
    const activeStreamConversationTitle =
      conversations.find((conversation) => conversation.id === activeStreamConversationId)?.title ||
      null;

    dispatchClawStreamStatus({
      sending: Boolean(activeStreamConversationId),
      conversationId: activeStreamConversationId,
      conversationTitle: activeStreamConversationTitle,
    });
  }, [conversationSessions, conversations, currentConvId]);

  useEffect(() => {
    if (!currentConvId) {
      return;
    }

    if (currentSession?.hasLoadedHistory || currentSession?.messagesLoading) {
      return;
    }

    let cancelled = false;

    updateConversationSession(currentConvId, (session) =>
      session.messagesLoading
        ? session
        : {
            ...session,
            messagesLoading: true,
          },
    );

    const loadMessages = async () => {
      try {
        const messages = await clawApi.getMessages(currentConvId);
        if (cancelled) {
          return;
        }

        updateConversationSession(currentConvId, (session) => ({
          ...session,
          timeline:
            session.sending || session.timeline.items.length > 0
              ? session.timeline
              : timelineReducer(session.timeline, {
                  type: "reset",
                  items: buildHistoryTimeline(messages),
                }),
          messagesLoading: false,
          hasLoadedHistory: true,
        }));
      } catch {
        if (cancelled) {
          return;
        }

        updateConversationSession(currentConvId, (session) => ({
          ...session,
          messagesLoading: false,
        }));
        message.error("加载消息失败");
      }
    };

    void loadMessages();

    return () => {
      cancelled = true;
    };
  }, [
    currentConvId,
    currentSession?.hasLoadedHistory,
    updateConversationSession,
  ]);

  useEffect(() => {
    setIsPinnedToBottom(true);
    setPendingMessageCount(0);
    shouldSnapToBottomRef.current = true;
    lastSeenItemCountRef.current = 0;
    setSelectedSkill(null);
  }, [currentConvId]);

  const isNearBottom = useCallback((container: HTMLDivElement | null) => {
    if (!container) {
      return true;
    }

    const distanceFromBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight;
    return distanceFromBottom <= BOTTOM_LOCK_THRESHOLD;
  }, []);

  const acknowledgeLatest = useCallback((latestCount: number) => {
    lastSeenItemCountRef.current = latestCount;
    setPendingMessageCount(0);
  }, []);

  const scrollTimelineToBottom = useCallback(
    (behavior: ScrollBehavior = "smooth") => {
      const container = timelineContainerRef.current;
      if (!container) {
        return;
      }

      container.scrollTo({ top: container.scrollHeight, behavior });
      setIsPinnedToBottom(true);
      acknowledgeLatest(timelineItemCount);
    },
    [acknowledgeLatest, timelineItemCount],
  );

  useEffect(() => {
    let frameId: number | null = null;

    if (shouldSnapToBottomRef.current || isPinnedToBottom) {
      shouldSnapToBottomRef.current = false;
      frameId = window.requestAnimationFrame(() => {
        scrollTimelineToBottom(sending ? "smooth" : "auto");
      });
    } else if (timelineItemCount > lastSeenItemCountRef.current) {
      setPendingMessageCount(timelineItemCount - lastSeenItemCountRef.current);
    } else if (sending) {
      setPendingMessageCount((count) => Math.max(count, 1));
    }

    return () => {
      if (frameId !== null) {
        window.cancelAnimationFrame(frameId);
      }
    };
  }, [timelineState.items, timelineItemCount, isPinnedToBottom, scrollTimelineToBottom, sending]);

  useEffect(() => () => {
    Object.values(activeRequestControllersRef.current).forEach((controller) => controller?.abort());
  }, []);

  useEffect(() => () => {
    dispatchClawStreamStatus({
      sending: false,
      conversationId: null,
      conversationTitle: null,
    });
  }, []);

  useEffect(() => {
    if (!active) {
      return;
    }

    const frameId = window.requestAnimationFrame(() => {
      scrollTimelineToBottom(sending ? "smooth" : "auto");
    });

    return () => {
      window.cancelAnimationFrame(frameId);
    };
  }, [active, scrollTimelineToBottom, sending]);

  const handleTimelineScroll = useCallback(() => {
    const container = timelineContainerRef.current;
    const nextPinnedState = isNearBottom(container);

    setIsPinnedToBottom((current) => (current === nextPinnedState ? current : nextPinnedState));

    if (nextPinnedState) {
      acknowledgeLatest(timelineItemCount);
      shouldSnapToBottomRef.current = false;
    }
  }, [acknowledgeLatest, isNearBottom, timelineItemCount]);

  const handleStopMessage = () => {
    if (!currentConvId || !sending) {
      return;
    }

    abortRequestedRef.current[currentConvId] = true;
    activeRequestControllersRef.current[currentConvId]?.abort();
    activeRequestControllersRef.current[currentConvId] = null;
    updateConversationSession(currentConvId, (session) => ({
      ...session,
      sending: false,
      timeline: timelineReducer(session.timeline, { type: "finalizeStream" }),
    }));
    message.info("已终止当前回复");
  };

  const handleSelectSlashSkill = (skill: ClawSkillSummary) => {
    setSelectedSkill(skill);
    setInputValue(slashDraft?.remainder || "");
  };

  const handleSendMessage = async () => {
    if (!currentConvId || sending) {
      return;
    }

    const conversationId = currentConvId;

    let turnSkill = selectedSkill;
    let userMessage = inputValue.trim();

    if (!turnSkill && userMessage) {
      const draft = getSlashDraft(userMessage);
      if (draft) {
        const exactMatches = findExactSkillMatches(availableSkills, draft.query);
        if (exactMatches.length === 1) {
          turnSkill = exactMatches[0];
          if (!draft.remainder) {
            setSelectedSkill(exactMatches[0]);
            setInputValue("");
            message.info(`已选择 /${getPreferredSkillAlias(exactMatches[0])}，请输入本轮消息内容。`);
            return;
          }
          userMessage = draft.remainder;
        }
      }
    }

    if (!userMessage && attachedImages.length === 0) {
      return;
    }
    const buildContent = (): string | ContentBlock[] => {
      if (attachedImages.length === 0) {
        return userMessage;
      }
      const blocks: ContentBlock[] = [];
      if (userMessage.trim()) {
        blocks.push({ type: "text", text: userMessage });
      }
      attachedImages.forEach((url) => {
        blocks.push({ type: "image_url", image_url: { url } });
      });
      return blocks;
    };
    const messageContent = buildContent();
    const controller = new AbortController();
    abortRequestedRef.current[conversationId] = false;
    activeRequestControllersRef.current[conversationId] = controller;
    shouldSnapToBottomRef.current = true;
    setInputValue("");
    setAttachedImages([]);
    setSelectedSkill(null);
    updateConversationSession(conversationId, (session) => {
      const withUserMessage = timelineReducer(session.timeline, {
        type: "appendUser",
        content: typeof messageContent === "string" ? messageContent : userMessage,
        selectedSkill: turnSkill ? getPreferredSkillAlias(turnSkill) : undefined,
      });
      const withAssistantTurn = timelineReducer(withUserMessage, { type: "startAssistantTurn" });

      return {
        ...session,
        timeline: withAssistantTurn,
        messagesLoading: false,
        sending: true,
        hasLoadedHistory: true,
      };
    });

    try {
      await clawApi.sendMessage(
        conversationId,
        { content: messageContent, selected_skill: turnSkill?.name },
        (event) => {
          applyTimelineAction(conversationId, { type: "applyEvent", event });
          if (event.type === "error") {
            message.error(event.message || "对话流出错");
          }
        },
        (error) => {
          if (abortRequestedRef.current[conversationId] && isAbortLikeError(error)) {
            return;
          }
          applyTimelineAction(conversationId, { type: "finalizeStream" });
          message.error(`连接失败: ${error.message}`);
        },
        controller.signal,
      );
    } catch (error) {
      if (abortRequestedRef.current[conversationId] && isAbortLikeError(error)) {
        return;
      }
      applyTimelineAction(conversationId, { type: "finalizeStream" });
      message.error(error instanceof Error ? error.message : "发送消息失败");
    } finally {
      if (activeRequestControllersRef.current[conversationId] === controller) {
        activeRequestControllersRef.current[conversationId] = null;
      }
      abortRequestedRef.current[conversationId] = false;
      updateConversationSession(conversationId, (session) =>
        session.sending
          ? {
              ...session,
              sending: false,
            }
          : session,
      );
    }
  };

  const handleCreateConversation = async () => {
    try {
      const values = await createForm.validateFields();
      const conversation = await clawApi.createConversation({
        title: values.title || "新对话",
        working_directory: values.working_directory,
        llm_model: values.llm_model || "deepseek-chat",
      });
      message.success("对话创建成功");
      setCreateModalOpen(false);
      createForm.resetFields();
      updateConversationSession(conversation.id, () => ({
        ...createInitialConversationSessionState(),
        hasLoadedHistory: true,
      }));
      await loadConversations();
      setCurrentConvId(conversation.id);
    } catch (error: unknown) {
      if (typeof error === "object" && error && "errorFields" in error) {
        return;
      }
      message.error("创建对话失败");
    }
  };

  const renderTimelineItem = (item: ChatTimelineItem) => {
    if (item.kind === "bubble") {
      const isUser = item.role === "user";
      if (!isUser) {
        return (
          <div
            key={item.id}
            style={{
              position: "relative",
              marginBottom: 12,
              paddingLeft: 74,
            }}
          >
            <div
              style={{
                position: "absolute",
                left: 58,
                top: 8,
                bottom: 0,
                width: 1,
                background: "rgba(82, 196, 26, 0.2)",
              }}
            />
            <div
              style={{
                position: "absolute",
                left: 54,
                top: 7,
                width: 9,
                height: 9,
                borderRadius: "50%",
                background: "#52c41a",
                boxShadow: "0 0 0 4px rgba(82, 196, 26, 0.12)",
              }}
            />
            <div
              style={{
                color: "#262626",
                minWidth: 0,
                wordBreak: "break-word",
              }}
            >
              {item.content ? (
                <ReactMarkdown>{item.content}</ReactMarkdown>
              ) : item.isStreaming ? (
                <Spin size="small" />
              ) : (
                <span style={{ color: "#8c8c8c" }}>(empty message)</span>
              )}
            </div>
          </div>
        );
      }

      return (
        <div key={item.id} style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
          <Avatar icon={<UserOutlined />} style={{ backgroundColor: "#1677ff", flexShrink: 0 }} />
          <div
            style={{
              flex: 1,
              minWidth: 0,
              padding: "14px 16px",
              borderRadius: 14,
              background: "#f5f5f5",
              boxShadow: "none",
            }}
          >
            {item.selectedSkill ? (
              <div style={{ marginBottom: 10 }}>
                <Tag color="processing">{`Skill: /${item.selectedSkill}`}</Tag>
              </div>
            ) : null}
            {item.content ? (
              <div style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{item.content}</div>
            ) : item.isStreaming ? (
              <Spin size="small" />
            ) : (
              <span style={{ color: "#8c8c8c" }}>(empty message)</span>
            )}
            {item.promptDebug ? <PromptDebugPanel snapshot={item.promptDebug} /> : null}
          </div>
        </div>
      );
    }

    const wrapperStyle = { paddingLeft: 52 };

    if (item.kind === "tool") {
      return (
        <div key={item.id} style={wrapperStyle}>
          <ToolCallCard
            toolCall={{
              id: item.toolId,
              toolName: item.toolName,
              status: item.status,
              input: item.input,
              output: item.output,
              error: item.error,
            }}
          />
        </div>
      );
    }

    if (item.kind === "shell") {
      return (
        <div key={item.id} style={wrapperStyle}>
          <ShellExecutionCard
            title={item.title}
            status={item.status}
            command={item.command}
            input={item.input}
            stdout={item.stdout}
            stderr={item.stderr}
            exitCode={item.exitCode}
          />
        </div>
      );
    }

    if (item.kind === "planning") {
      if (item.todos.length === 0) {
        return null;
      }

      return (
        <div key={item.id} style={wrapperStyle}>
          <PlanningCard title={item.title} status={item.status} todos={item.todos} />
        </div>
      );
    }

    return (
      <div key={item.id} style={wrapperStyle}>
        <SubAgentCard
          title={item.title}
          status={item.status}
          toolId={item.toolId}
          transcript={item.transcript}
          result={item.result}
          childTools={item.childTools}
        />
      </div>
    );
  };

  const renderConversationList = () => (
    <>
      <div style={{ padding: "8px 12px", borderBottom: "1px solid #f0f0f0" }}>
        <Input
          placeholder="搜索对话..."
          prefix={<SearchOutlined style={{ color: "#999" }} />}
          value={searchKeyword}
          onChange={(event) => setSearchKeyword(event.target.value)}
          allowClear
          size="small"
        />
      </div>
      {convLoading ? (
        <div style={{ textAlign: "center", padding: 24 }}>
          <Spin />
        </div>
      ) : filteredConversations.length === 0 ? (
        <Empty
          description={searchKeyword ? "没有匹配的对话" : "暂无对话"}
          style={{ marginTop: 40 }}
        />
      ) : (
        <Menu
          mode="inline"
          selectedKeys={currentConvId ? [currentConvId] : []}
          style={{ border: "none" }}
          items={filteredConversations.map((conversation) => ({
            key: conversation.id,
            icon: <MessageOutlined />,
            label: (
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span>{conversation.title}</span>
                <Popconfirm
                  title="确定删除这个对话？"
                  onConfirm={(event) => {
                    event?.stopPropagation();
                    void clawApi
                      .deleteConversation(conversation.id)
                      .then(async () => {
                        clearConversationSession(conversation.id);
                        message.success("对话已删除");
                        await loadConversations();
                        if (currentConvId === conversation.id) {
                          setCurrentConvId(null);
                        }
                      })
                      .catch(() => message.error("删除对话失败"));
                  }}
                  okText="删除"
                  cancelText="取消"
                >
                  <DeleteOutlined
                    style={{ color: "#ff4d4f" }}
                    onClick={(event) => event.stopPropagation()}
                  />
                </Popconfirm>
              </div>
            ),
            onClick: () => setCurrentConvId(conversation.id),
          }))}
        />
      )}
    </>
  );

  const showJumpToLatest =
    Boolean(currentConvId) && !isPinnedToBottom && (pendingMessageCount > 0 || sending);
  const showComposerStatus = sending || showJumpToLatest;
  const composerStatusText = sending
    ? "\u6b63\u5728\u751f\u6210\u56de\u590d\uff0c\u8f93\u5165\u6846\u4f1a\u4fdd\u6301\u56fa\u5b9a\u3002"
    : pendingMessageCount > 0
      ? `${pendingMessageCount} \u6761\u65b0\u6d88\u606f\uff0c\u70b9\u51fb\u53f3\u4e0b\u89d2\u56de\u5230\u5e95\u90e8\u3002`
      : "\u6709\u65b0\u7684\u6d41\u5f0f\u5185\u5bb9\uff0c\u70b9\u51fb\u53f3\u4e0b\u89d2\u56de\u5230\u5e95\u90e8\u3002";

  return (
    <div
      style={{
        display: "flex",
        height: CHAT_VIEWPORT_HEIGHT,
        minHeight: 0,
        padding: 16,
        gap: 16,
        overflow: "hidden",
      }}
    >
      <Drawer
        title="对话历史"
        placement="left"
        open={sidebarDrawerOpen}
        onClose={() => setSidebarDrawerOpen(false)}
        width={280}
        bodyStyle={{ padding: 0 }}
      >
        {renderConversationList()}
      </Drawer>

      {!isMobile && (
        <Card
          title="对话历史"
          style={{ width: 280, display: "flex", flexDirection: "column", height: "100%", minHeight: 0 }}
          bodyStyle={{ flex: 1, overflow: "auto", padding: 0, minHeight: 0 }}
          extra={(
            <Tooltip title="新建对话">
              <Button
                type="primary"
                icon={<PlusOutlined />}
                size="small"
                onClick={() => setCreateModalOpen(true)}
              >
                新建
              </Button>
            </Tooltip>
          )}
        >
          {renderConversationList()}
        </Card>
      )}

      <Card
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          height: "100%",
          minHeight: 0,
          overflow: "hidden",
        }}
        bodyStyle={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          padding: 0,
          minHeight: 0,
          overflow: "hidden",
        }}
        title={(
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            {isMobile && <MenuOutlined onClick={() => setSidebarDrawerOpen(true)} />}
            <span>Claw 对话龙虾</span>
          </div>
        )}
        extra={(
          <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
            <Input
              prefix={<FolderOutlined />}
              value={workingDirectory}
              readOnly
              style={{ width: 220 }}
              size="small"
            />
            <Select
              value={selectedModel}
              disabled
              style={{ width: 170 }}
              size="small"
              options={models.map((model) => ({ label: model.name, value: model.model_id }))}
            />
          </div>
        )}
      >
        <div style={{ flex: 1, minHeight: 0, position: "relative", overflow: "hidden" }}>
          <div
            ref={timelineContainerRef}
            onScroll={handleTimelineScroll}
            style={{
              height: "100%",
              overflowY: "auto",
              overflowX: "hidden",
              padding: "20px 20px 28px",
              background: "#fafafa",
            }}
          >
          {!currentConvId ? (
            <Empty description="选择或创建对话后开始聊天" />
          ) : messagesLoading ? (
            <div style={{ textAlign: "center", padding: 40 }}>
              <Spin />
            </div>
          ) : displayTimelineItems.length === 0 ? (
            <Empty description="暂无消息，开始对话吧" />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {displayTimelineItems.map(renderTimelineItem)}
            </div>
          )}
          </div>

          {showJumpToLatest ? (
            <Button
              type="primary"
              icon={<ArrowDownOutlined />}
              onClick={() => scrollTimelineToBottom("smooth")}
              shape={isMobile ? "circle" : undefined}
              style={{
                position: "absolute",
                right: 16,
                bottom: 16,
                boxShadow: "0 10px 24px rgba(22, 119, 255, 0.24)",
              }}
            >
              {!isMobile
                ? pendingMessageCount > 0
                  ? `\u56de\u5230\u6700\u65b0\u6d88\u606f ${pendingMessageCount}`
                  : "\u56de\u5230\u6700\u65b0\u6d88\u606f"
                : null}
            </Button>
          ) : null}
        </div>

        <div
          style={{
            padding: 16,
            borderTop: "1px solid #f0f0f0",
            background: "#fff",
            boxShadow: "0 -8px 24px rgba(15, 23, 42, 0.04)",
            position: "relative",
            zIndex: 1,
          }}
        >
          {selectedSkill ? (
            <div style={{ marginBottom: 10 }}>
              <Tag
                color="processing"
                closable
                onClose={(event) => {
                  event.preventDefault();
                  setSelectedSkill(null);
                }}
              >
                {`本轮技能 /${getPreferredSkillAlias(selectedSkill)}`}
              </Tag>
            </div>
          ) : null}
          {showComposerStatus ? (
            <div
              style={{
                marginBottom: 10,
                padding: "8px 12px",
                borderRadius: 10,
                background: sending ? "#e6f4ff" : "#f6ffed",
                border: `1px solid ${sending ? "#91caff" : "#b7eb8f"}`,
                color: sending ? "#0958d9" : "#389e0d",
                fontSize: 12,
                lineHeight: 1.4,
              }}
            >
              {composerStatusText}
            </div>
          ) : null}
          {!selectedSkill && slashSuggestions.length > 0 ? (
            <div
              style={{
                marginBottom: 10,
                border: "1px solid #d9d9d9",
                borderRadius: 12,
                background: "#ffffff",
                boxShadow: "0 10px 24px rgba(15, 23, 42, 0.08)",
                overflow: "hidden",
              }}
            >
              {slashSuggestions.map((skill, index) => (
                <button
                  key={skill.name}
                  type="button"
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => handleSelectSlashSkill(skill)}
                  style={{
                    width: "100%",
                    padding: "12px 14px",
                    textAlign: "left",
                    background: "transparent",
                    border: "none",
                    borderBottom:
                      index === slashSuggestions.length - 1 ? "none" : "1px solid #f0f0f0",
                    cursor: "pointer",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600 }}>{`/${getPreferredSkillAlias(skill)}`}</span>
                    {skill.name !== getPreferredSkillAlias(skill) ? (
                      <Tag style={{ marginInlineEnd: 0 }}>{skill.name}</Tag>
                    ) : null}
                  </div>
                  <div style={{ color: "#8c8c8c", fontSize: 12, lineHeight: 1.5 }}>
                    {skill.description}
                  </div>
                </button>
              ))}
            </div>
          ) : null}
          <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
            <Input.TextArea
              value={inputValue}
              onChange={(event) => setInputValue(event.target.value)}
              placeholder="输入消息..."
              autoSize={{ minRows: 1, maxRows: 4 }}
              disabled={!currentConvId || sending}
              onPressEnter={(event) => {
                if (!event.shiftKey) {
                  event.preventDefault();
                  void handleSendMessage();
                }
              }}
            />
            {sending ? (
              <Button danger icon={<CloseCircleOutlined />} onClick={handleStopMessage}>
                终止
              </Button>
            ) : (
              <Button
                type="primary"
                icon={<SendOutlined />}
                onClick={() => void handleSendMessage()}
                disabled={!currentConvId || !inputValue.trim()}
              >
                发送
              </Button>
            )}
          </div>
        </div>
      </Card>

      <Modal
        title="新建对话"
        open={createModalOpen}
        onOk={() => void handleCreateConversation()}
        onCancel={() => {
          setCreateModalOpen(false);
          createForm.resetFields();
        }}
        okText="创建"
        cancelText="取消"
      >
        <Form form={createForm} layout="vertical" initialValues={{ llm_model: "deepseek-chat" }}>
          <Form.Item label="对话标题" name="title">
            <Input placeholder="可选，默认使用“新对话”" />
          </Form.Item>
          <Form.Item
            label="工作目录"
            name="working_directory"
            rules={[{ required: true, message: "请选择或输入工作目录" }]}
          >
            <Input
              prefix={<FolderOutlined />}
              placeholder="例如：C:\\Users\\YourName\\Projects"
              addonAfter={(
                <Button
                  type="link"
                  size="small"
                  onClick={() => setDirectoryBrowserOpen(true)}
                  style={{ padding: 0 }}
                >
                  浏览
                </Button>
              )}
            />
          </Form.Item>
          <Form.Item label="LLM 模型" name="llm_model">
            <Select options={models.map((model) => ({ label: model.name, value: model.model_id }))} />
          </Form.Item>
        </Form>
      </Modal>

      <DirectoryBrowser
        open={directoryBrowserOpen}
        onCancel={() => setDirectoryBrowserOpen(false)}
        onSelect={(path) => createForm.setFieldsValue({ working_directory: path })}
      />
    </div>
  );
};

export default ClawChatPage;
