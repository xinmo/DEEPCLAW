import React from "react";
import { Button, Card, Tag, Typography } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  CodeOutlined,
  LoadingOutlined,
} from "@ant-design/icons";

import type { ProcessStatus } from "../../types/claw";

const { Text } = Typography;

interface ShellExecutionCardProps {
  title: string;
  status: ProcessStatus;
  command: string;
  input?: unknown;
  stdout?: string;
  stderr?: string;
  exitCode?: number;
}

function prettyValue(value: unknown) {
  if (typeof value === "string") {
    return value;
  }

  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function inferCommandFromOutput(text?: string) {
  if (!text) {
    return "";
  }

  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line) {
      continue;
    }

    const patterns = [
      /^'([^'\r\n]+)'\s+不是内部或外部命令/i,
      /^'([^'\r\n]+)'\s+is not recognized as an internal or external command/i,
      /^([^:\r\n]+)\s*:\s+The term '([^'\r\n]+)' is not recognized as the name of a cmdlet/i,
      /^(?:\/bin\/sh:\s*\d+:\s*)?([^\s:]+):\s+(?:not found|command not found)/i,
      /^bash:\s+([^\s:]+):\s+command not found/i,
    ];

    for (const pattern of patterns) {
      const match = line.match(pattern);
      if (!match) {
        continue;
      }

      for (const value of match.slice(1)) {
        if (value && value.trim()) {
          return value.trim();
        }
      }
    }
  }

  return "";
}

function buildInputPreview(command: string, input: unknown, stdout?: string, stderr?: string) {
  const trimmedCommand = command.trim();
  const inferredCommand = inferCommandFromOutput(stderr) || inferCommandFromOutput(stdout);
  const displayCommand = trimmedCommand || inferredCommand;

  if (!input || typeof input !== "object" || Array.isArray(input)) {
    return displayCommand || (input ? prettyValue(input) : "<no input captured>");
  }

  const record = input as Record<string, unknown>;
  const extras = Object.fromEntries(
    Object.entries(record).filter(([key, value]) => {
      if (["command", "cmd", "script", "commands", "args"].includes(key)) {
        return false;
      }
      if (value === undefined || value === null || value === "") {
        return false;
      }
      if (Array.isArray(value) && value.length === 0) {
        return false;
      }
      return true;
    }),
  );

  if (Object.keys(record).length === 0) {
    return displayCommand || "<no input captured>";
  }

  if (displayCommand && Object.keys(extras).length === 0) {
    return displayCommand;
  }

  if (displayCommand && Object.keys(extras).length > 0) {
    return `${displayCommand}\n${prettyValue(extras)}`;
  }

  if (Object.keys(extras).length > 0) {
    return prettyValue(extras);
  }

  return prettyValue(record);
}

function buildOutputPreview(stdout?: string, stderr?: string, exitCode?: number) {
  const parts: string[] = [];

  if (stdout && stdout.trim()) {
    parts.push(stdout.trimEnd());
  }

  if (stderr && stderr.trim()) {
    parts.push(`[stderr]\n${stderr.trimEnd()}`);
  }

  if (exitCode !== undefined) {
    parts.push(`Exit code: ${exitCode}`);
  }

  if (parts.length === 0) {
    return "<no output>";
  }

  return parts.join("\n\n");
}

function IoRow({ label, content }: { label: "IN" | "OUT"; content: string }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "44px 1fr",
        gap: 10,
        alignItems: "start",
      }}
    >
      <div
        style={{
          color: "rgba(255,255,255,0.52)",
          fontSize: 11,
          fontWeight: 700,
          letterSpacing: 0.8,
          lineHeight: "30px",
          textAlign: "center",
          borderRight: "1px solid rgba(148,163,184,0.18)",
        }}
      >
        {label}
      </div>
      <pre
        style={{
          margin: 0,
          padding: "8px 12px 8px 0",
          color: "#f3f4f6",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          overflowX: "auto",
          fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace",
          fontSize: 12,
          lineHeight: 1.6,
        }}
      >
        {content}
      </pre>
    </div>
  );
}

function buildCollapsedOutput(content: string, maxLines: number) {
  const lines = content.split(/\r?\n/);
  if (lines.length <= maxLines) {
    return { content, truncated: false, totalLines: lines.length };
  }

  return {
    content: `${lines.slice(0, maxLines).join("\n")}\n...`,
    truncated: true,
    totalLines: lines.length,
  };
}

function buildDisplayTitle(title: string, command: string) {
  const trimmedCommand = command.trim();
  if (trimmedCommand) {
    return trimmedCommand;
  }

  const normalizedTitle = title.trim().toLowerCase();
  if (normalizedTitle && !["shell", "bash", "execute"].includes(normalizedTitle)) {
    return title.trim();
  }

  return "Bash";
}

const ShellExecutionCard: React.FC<ShellExecutionCardProps> = ({
  title,
  status,
  command,
  input,
  stdout,
  stderr,
  exitCode,
}) => {
  const icon =
    status === "running" ? (
      <LoadingOutlined style={{ color: "#1677ff" }} />
    ) : status === "success" || status === "completed" ? (
      <CheckCircleOutlined style={{ color: "#52c41a" }} />
    ) : status === "failed" ? (
      <CloseCircleOutlined style={{ color: "#ff4d4f" }} />
    ) : (
      <CodeOutlined style={{ color: "#1677ff" }} />
    );

  const tagColor =
    status === "running"
      ? "processing"
      : status === "success" || status === "completed"
        ? "success"
      : status === "failed"
          ? "error"
          : "default";

  const inferredCommand = inferCommandFromOutput(stderr) || inferCommandFromOutput(stdout);
  const displayTitle = buildDisplayTitle(title, command || inferredCommand);
  const inputPreview = buildInputPreview(command, input, stdout, stderr);
  const outputPreview = buildOutputPreview(stdout, stderr, exitCode);
  const [isOutputExpanded, setIsOutputExpanded] = React.useState(false);
  const collapsedOutput = buildCollapsedOutput(outputPreview, 3);
  const visibleOutput = isOutputExpanded || !collapsedOutput.truncated ? outputPreview : collapsedOutput.content;

  return (
    <Card
      size="small"
      style={{
        marginBottom: 10,
        borderRadius: 12,
        background: "#f6ffed",
        borderColor: status === "failed" ? "#ffccc7" : "#b7eb8f",
      }}
      bodyStyle={{ padding: 14 }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10, minWidth: 0 }}>
        {icon}
        <Text
          strong
          ellipsis={{ tooltip: displayTitle }}
          style={{ flex: 1, minWidth: 0 }}
        >
          {displayTitle}
        </Text>
        <Tag color={tagColor}>{status}</Tag>
        {exitCode !== undefined && <Tag>exit {exitCode}</Tag>}
      </div>

      <div
        style={{
          overflow: "hidden",
          borderRadius: 8,
          background: "#111827",
          border: "1px solid rgba(148,163,184,0.22)",
        }}
      >
        <IoRow label="IN" content={inputPreview} />
        <div style={{ borderTop: "1px solid rgba(148,163,184,0.18)" }} />
        <IoRow label="OUT" content={visibleOutput} />
        {collapsedOutput.truncated && (
          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              padding: "0 12px 10px 0",
            }}
          >
            <Button
              type="link"
              size="small"
              style={{ color: "#93c5fd", paddingInline: 0 }}
              onClick={() => setIsOutputExpanded((value) => !value)}
            >
              {isOutputExpanded
                ? "收起输出"
                : `展开输出 (${collapsedOutput.totalLines} 行)`}
            </Button>
          </div>
        )}
      </div>
    </Card>
  );
};

export default ShellExecutionCard;
