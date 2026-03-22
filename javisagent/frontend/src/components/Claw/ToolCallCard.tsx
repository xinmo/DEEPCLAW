import React, { useState } from "react";
import { Card, Collapse, List, Tag, Typography } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  EditOutlined,
  FileTextOutlined,
  FolderOpenOutlined,
  LinkOutlined,
  LoadingOutlined,
  SearchOutlined,
  ToolOutlined,
} from "@ant-design/icons";

import type { ToolCall, ToolStatus } from "../../types/claw";

const { Text, Paragraph } = Typography;

const FILE_TOOL_NAMES = new Set(["read_file", "write_file", "edit_file", "glob", "grep", "ls"]);
const SEARCH_FILE_TOOL_NAMES = new Set(["glob", "grep", "ls"]);

interface ToolCallCardProps {
  toolCall: ToolCall;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function getParsedToolInput(toolCall: ToolCall): unknown {
  return parseMaybeJson(toolCall.input);
}

function getToolInputRecord(toolCall: ToolCall): Record<string, unknown> | null {
  const parsed = getParsedToolInput(toolCall);
  return isRecord(parsed) ? parsed : null;
}

function getRawToolInputText(toolCall: ToolCall): string {
  const parsed = getParsedToolInput(toolCall);
  if (typeof parsed === "string" && parsed.trim()) {
    return normalizeTextPaths(parsed.trim());
  }
  if (Array.isArray(parsed) && parsed.length > 0) {
    return prettyValue(parsed);
  }
  if (isRecord(parsed) && Object.keys(parsed).length > 0) {
    return prettyValue(parsed);
  }
  return "";
}

function prettyValue(value: unknown): string {
  if (typeof value === "string") {
    return normalizeTextPaths(value);
  }

  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function parseMaybeJson(value: unknown): unknown {
  if (typeof value !== "string") {
    return value;
  }

  const trimmed = value.trim();
  if (!trimmed.startsWith("{") && !trimmed.startsWith("[")) {
    return value;
  }

  try {
    return JSON.parse(trimmed);
  } catch {
    return value;
  }
}

function getStringValueFromRecord(record: Record<string, unknown>, keys: string[]): string {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
    if (Array.isArray(value)) {
      const parts = value
        .map((item) => (typeof item === "string" ? item.trim() : ""))
        .filter(Boolean);
      if (parts.length > 0) {
        return parts.join(", ");
      }
    }
  }

  return "";
}

function formatSearchRecordEntry(record: Record<string, unknown>): string[] {
  for (const key of ["results", "matches", "files", "items", "entries", "paths", "data"]) {
    if (record[key] !== undefined) {
      const nestedEntries = getSearchCollectionEntries(record[key]);
      if (nestedEntries.length > 0) {
        return nestedEntries;
      }
    }
  }

  const path = getStringValueFromRecord(record, ["path", "file_path", "filepath", "file", "name"]);
  const normalizedPath = path ? normalizeDisplayPath(path) : "";
  const line = typeof record.line === "number" ? `:${record.line}` : "";
  const text = getStringValueFromRecord(record, ["text", "preview", "content", "message"]);
  const normalizedText = text ? normalizeTextPaths(text) : "";

  if (normalizedPath || normalizedText) {
    return [`${normalizedPath}${line}${normalizedText ? ` ${normalizedText}` : ""}`.trim()];
  }

  return [];
}

function extractListEntriesFromString(value: string): string[] {
  const trimmed = value.trim();
  if (!trimmed) {
    return [];
  }

  const parsed = parseMaybeJson(trimmed);
  if (parsed !== trimmed) {
    return getSearchCollectionEntries(parsed);
  }

  const quotedMatches = [...trimmed.matchAll(/['"]([^'"]+)['"]/g)]
    .map((match) => match[1]?.trim())
    .filter((entry): entry is string => Boolean(entry));
  if (trimmed.startsWith("[") && trimmed.endsWith("]") && quotedMatches.length > 0) {
    return quotedMatches.map((entry) => normalizeDisplayPath(entry));
  }

  if (trimmed === "[]" || trimmed === "{}") {
    return [];
  }

  return normalizeTextPaths(trimmed)
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function getSearchCollectionEntries(output: unknown): string[] {
  if (typeof output === "string") {
    return extractListEntriesFromString(output);
  }

  const parsed = parseMaybeJson(output);
  if (Array.isArray(parsed)) {
    return parsed.flatMap((item) => getSearchCollectionEntries(item)).filter(Boolean);
  }

  if (isRecord(parsed)) {
    return formatSearchRecordEntry(parsed);
  }

  return [];
}

function normalizeDisplayPath(path: string): string {
  const windowsVirtualMatch = path.match(/^\/([a-zA-Z])\/(.+)$/);
  if (!windowsVirtualMatch) {
    return path;
  }

  const [, drive, suffix] = windowsVirtualMatch;
  return `${drive.toUpperCase()}:\\${suffix.replaceAll("/", "\\")}`;
}

function normalizeTextPaths(text: string): string {
  return text.replace(/\/([a-zA-Z])\/[^\s)"'`]+/g, (match) => normalizeDisplayPath(match));
}

function getStatusLabel(status: ToolStatus) {
  if (status === "running") {
    return "running";
  }
  if (status === "success") {
    return "success";
  }
  return "failed";
}

function getStatusColor(status: ToolStatus) {
  if (status === "running") {
    return "#1677ff";
  }
  if (status === "success") {
    return "#52c41a";
  }
  return "#ff4d4f";
}

function getToolPathValue(toolCall: ToolCall) {
  const input = getToolInputRecord(toolCall);
  if (!input) {
    return "";
  }

  const value = getStringValueFromRecord(input, [
    "file_path",
    "path",
    "target_path",
    "read_file_path",
    "cwd",
    "directory",
    "base_path",
    "root",
    "search_path",
    "folder",
  ]);

  return value ? normalizeDisplayPath(value) : "";
}

function getToolPatternValue(toolCall: ToolCall) {
  const input = getToolInputRecord(toolCall);
  if (input) {
    const value = getStringValueFromRecord(input, [
      "pattern",
      "query",
      "glob",
      "search",
      "include",
      "glob_pattern",
      "file_pattern",
      "match",
    ]);
    if (value) {
      return value;
    }
  }

  return getRawToolInputText(toolCall);
}

function buildSearchTarget(toolCall: ToolCall): string {
  const pattern = getToolPatternValue(toolCall);
  const path = getToolPathValue(toolCall);
  const parts: string[] = [];

  if (pattern) {
    parts.push(pattern);
  }

  if (path) {
    parts.push(`in ${path}`);
  }

  return parts.join(" ");
}

function buildSearchInputLines(toolCall: ToolCall): string[] {
  const pattern = getToolPatternValue(toolCall);
  const path = getToolPathValue(toolCall);
  const input = getToolInputRecord(toolCall);
  const parsedInput = getParsedToolInput(toolCall);
  const lines: string[] = [];

  if (toolCall.toolName !== "ls" && pattern) {
    lines.push(`pattern: ${pattern}`);
  }

  if (path) {
    lines.push(`path: ${path}`);
  } else if (toolCall.toolName === "ls") {
    lines.push("path: /");
  }

  if (lines.length > 0) {
    return lines;
  }

  const rawInputText = getRawToolInputText(toolCall);
  if (rawInputText) {
    return rawInputText
      .split(/\r?\n/)
      .map((line) => line.trimEnd())
      .filter(Boolean)
      .slice(0, 4);
  }

  if (input && Object.keys(input).length > 0) {
    return prettyValue(input)
      .split(/\r?\n/)
      .map((line) => line.trimEnd())
      .filter(Boolean)
      .slice(0, 4);
  }

  if (Array.isArray(parsedInput) && parsedInput.length > 0) {
    return prettyValue(parsedInput)
      .split(/\r?\n/)
      .map((line) => line.trimEnd())
      .filter(Boolean)
      .slice(0, 4);
  }

  return [];
}

function getNumericInputValue(toolCall: ToolCall, key: string): number | null {
  const input = getToolInputRecord(toolCall);
  if (!input) {
    return null;
  }

  const value = input[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function getReadFileLineRange(toolCall: ToolCall): string {
  if (toolCall.toolName !== "read_file") {
    return "";
  }

  const offset = getNumericInputValue(toolCall, "offset");
  const limit = getNumericInputValue(toolCall, "limit");
  if (offset !== null) {
    const startLine = Math.max(1, Math.floor(offset) + 1);
    const safeLimit = limit !== null && limit > 0 ? Math.floor(limit) : null;
    if (safeLimit !== null) {
      return `(lines ${startLine}-${startLine + safeLimit - 1})`;
    }
    return `(line ${startLine})`;
  }

  if (typeof toolCall.output !== "string") {
    return "";
  }

  const matches = [...toolCall.output.matchAll(/^\s*(\d+)(?:\.\d+)?\t/gm)];
  if (matches.length === 0) {
    return "";
  }

  const firstLine = Number(matches[0][1]);
  const lastLine = Number(matches[matches.length - 1][1]);
  if (!Number.isFinite(firstLine) || !Number.isFinite(lastLine)) {
    return "";
  }
  if (firstLine === lastLine) {
    return `(line ${firstLine})`;
  }
  return `(lines ${firstLine}-${lastLine})`;
}

function summarizeToolInput(toolCall: ToolCall): string {
  if (toolCall.toolName === "web_search" && isRecord(toolCall.input)) {
    const query = toolCall.input.query;
    if (typeof query === "string" && query) {
      return query;
    }
  }

  if (toolCall.toolName === "fetch_url" && isRecord(toolCall.input)) {
    const url = toolCall.input.url;
    if (typeof url === "string" && url) {
      return url;
    }
  }

  return "";
}

function buildFileToolTitle(toolCall: ToolCall): { action: string; target: string } {
  if (toolCall.toolName === "read_file") {
    const path = getToolPathValue(toolCall);
    const lineRange = getReadFileLineRange(toolCall);
    return { action: "Read", target: [path, lineRange].filter(Boolean).join(" ") };
  }
  if (toolCall.toolName === "write_file") {
    return { action: "Write", target: getToolPathValue(toolCall) };
  }
  if (toolCall.toolName === "edit_file") {
    return { action: "Edit", target: getToolPathValue(toolCall) };
  }
  if (toolCall.toolName === "ls") {
    return { action: "List", target: getToolPathValue(toolCall) || "/" };
  }
  if (toolCall.toolName === "glob") {
    return { action: "Glob", target: buildSearchTarget(toolCall) };
  }
  if (toolCall.toolName === "grep") {
    return { action: "Grep", target: buildSearchTarget(toolCall) };
  }

  return { action: toolCall.toolName, target: "" };
}

function buildEditPreview(toolCall: ToolCall): string[] {
  if (!isRecord(toolCall.input)) {
    return [];
  }

  const oldValue = typeof toolCall.input.old_string === "string" ? toolCall.input.old_string : "";
  const newValue = typeof toolCall.input.new_string === "string" ? toolCall.input.new_string : "";
  const preview: string[] = [];

  if (oldValue) {
    preview.push(`- ${oldValue.split(/\r?\n/)[0]}`);
  }
  if (newValue) {
    preview.push(`+ ${newValue.split(/\r?\n/)[0]}`);
  }

  return preview.slice(0, 4);
}

function splitEditLines(value: string): string[] {
  if (!value) {
    return [];
  }

  return value.replace(/\r\n/g, "\n").split("\n");
}

function summarizeEditLineChanges(oldValue: string, newValue: string): string {
  const oldLines = splitEditLines(oldValue);
  const newLines = splitEditLines(newValue);

  if (oldLines.length === 0 && newLines.length === 0) {
    return "";
  }

  let sharedLineCount = 0;
  const complexity = oldLines.length * newLines.length;

  if (complexity > 40000) {
    sharedLineCount = 0;
  } else {
    let previous = new Array<number>(newLines.length + 1).fill(0);
    let current = new Array<number>(newLines.length + 1).fill(0);

    for (let oldIndex = 1; oldIndex <= oldLines.length; oldIndex += 1) {
      current[0] = 0;
      for (let newIndex = 1; newIndex <= newLines.length; newIndex += 1) {
        if (oldLines[oldIndex - 1] === newLines[newIndex - 1]) {
          current[newIndex] = previous[newIndex - 1] + 1;
        } else {
          current[newIndex] = Math.max(previous[newIndex], current[newIndex - 1]);
        }
      }
      [previous, current] = [current, previous];
    }

    sharedLineCount = previous[newLines.length];
  }

  const deletedCount = Math.max(oldLines.length - sharedLineCount, 0);
  const addedCount = Math.max(newLines.length - sharedLineCount, 0);
  const summaryParts: string[] = [];

  if (addedCount > 0) {
    summaryParts.push(`${addedCount} line${addedCount === 1 ? "" : "s"} added`);
  }
  if (deletedCount > 0) {
    summaryParts.push(`${deletedCount} line${deletedCount === 1 ? "" : "s"} deleted`);
  }

  if (summaryParts.length === 0) {
    return "No line changes";
  }

  return summaryParts.join(", ");
}

function buildSearchPreview(toolCall: ToolCall): string[] {
  const entries = getSearchCollectionEntries(toolCall.output);
  if (entries.length > 0) {
    return entries.slice(0, 8);
  }

  const parsed = parseMaybeJson(toolCall.output);

  if (typeof parsed === "string" && parsed.trim()) {
    return normalizeTextPaths(parsed)
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .slice(0, 5);
  }

  return [];
}

function buildFileToolSecondary(toolCall: ToolCall): string {
  if (toolCall.toolName === "read_file") {
    return "";
  }

  const parsedOutput = parseMaybeJson(toolCall.output);

  if (toolCall.toolName === "glob" || toolCall.toolName === "ls") {
    const entries = getSearchCollectionEntries(toolCall.output);
    if (entries.length > 0) {
      return `${entries.length} file${entries.length === 1 ? "" : "s"} found`;
    }
    if (Array.isArray(parsedOutput)) {
      return "No files found";
    }
  }

  if (toolCall.toolName === "grep") {
    const entries = getSearchCollectionEntries(toolCall.output);
    if (entries.length > 0) {
      return `${entries.length} match${entries.length === 1 ? "" : "es"} found`;
    }
    if (Array.isArray(parsedOutput)) {
      return "No matches found";
    }
  }

  if (toolCall.toolName === "write_file" && isRecord(toolCall.input)) {
    const content = toolCall.input.content;
    if (typeof content === "string" && content) {
      return `${content.split(/\r?\n/).length} lines written`;
    }
  }

  if (toolCall.toolName === "edit_file" && toolCall.status === "success" && isRecord(toolCall.input)) {
    const oldValue = typeof toolCall.input.old_string === "string" ? toolCall.input.old_string : "";
    const newValue = typeof toolCall.input.new_string === "string" ? toolCall.input.new_string : "";
    const summary = summarizeEditLineChanges(oldValue, newValue);
    if (summary) {
      return summary;
    }
  }

  if (typeof toolCall.output === "string" && toolCall.output.trim()) {
    return normalizeTextPaths(toolCall.output);
  }

  return "";
}

function buildFileToolPreview(toolCall: ToolCall): string[] {
  if (toolCall.toolName === "read_file") {
    return [];
  }

  if (toolCall.toolName === "edit_file") {
    return buildEditPreview(toolCall);
  }

  if (toolCall.toolName === "glob" || toolCall.toolName === "grep" || toolCall.toolName === "ls") {
    return buildSearchPreview(toolCall);
  }

  return [];
}

function getFileToolPreviewOverflow(toolCall: ToolCall, previewLines: string[]): number {
  if (toolCall.toolName === "read_file" && typeof toolCall.output === "string") {
    const total = normalizeTextPaths(toolCall.output).split(/\r?\n/).length;
    return Math.max(total - previewLines.length, 0);
  }

  const parsedOutput = parseMaybeJson(toolCall.output);
  if (SEARCH_FILE_TOOL_NAMES.has(toolCall.toolName)) {
    const entries = getSearchCollectionEntries(toolCall.output);
    if (entries.length > 0) {
      return Math.max(entries.length - previewLines.length, 0);
    }
    if (Array.isArray(parsedOutput)) {
      return 0;
    }
  }

  return 0;
}

function getFileToolIcon(toolName: string) {
  if (toolName === "edit_file") {
    return <EditOutlined />;
  }
  if (toolName === "glob" || toolName === "grep") {
    return <SearchOutlined />;
  }
  if (toolName === "ls") {
    return <FolderOpenOutlined />;
  }
  return <FileTextOutlined />;
}

function renderWebOutput(output: unknown): React.ReactNode {
  const parsed = parseMaybeJson(output);

  if (
    parsed &&
    typeof parsed === "object" &&
    "results" in parsed &&
    Array.isArray((parsed as Record<string, unknown>).results)
  ) {
    const results = (parsed as { results: Array<Record<string, unknown>> }).results;
    return (
      <List
        size="small"
        dataSource={results.slice(0, 5)}
        renderItem={(item, index) => (
          <List.Item
            key={`${String(item.url)}-${index}`}
            style={{
              padding: "12px 0",
              borderBottom: "1px solid #f0f0f0",
              alignItems: "flex-start",
            }}
          >
            <div style={{ width: "100%" }}>
              <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 6 }}>
                <SearchOutlined style={{ color: "#1677ff" }} />
                <Text strong>{String(item.title || `Result ${index + 1}`)}</Text>
              </div>
              {typeof item.url === "string" && (
                <a
                  href={item.url}
                  target="_blank"
                  rel="noreferrer"
                  style={{ display: "inline-flex", alignItems: "center", gap: 6, marginBottom: 6 }}
                >
                  <LinkOutlined />
                  <span>{item.url}</span>
                </a>
              )}
              {typeof item.content === "string" && (
                <Paragraph style={{ marginBottom: 0, whiteSpace: "pre-wrap" }}>
                  {item.content}
                </Paragraph>
              )}
            </div>
          </List.Item>
        )}
      />
    );
  }

  if (
    parsed &&
    typeof parsed === "object" &&
    "markdown_content" in parsed &&
    typeof (parsed as Record<string, unknown>).markdown_content === "string"
  ) {
    return (
      <Paragraph
        style={{
          marginBottom: 0,
          padding: 12,
          borderRadius: 8,
          background: "#fafafa",
          whiteSpace: "pre-wrap",
        }}
      >
        {(parsed as { markdown_content: string }).markdown_content}
      </Paragraph>
    );
  }

  return (
    <pre
      style={{
        margin: 0,
        padding: 12,
        background: "#fafafa",
        borderRadius: 8,
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
        overflowX: "auto",
      }}
    >
      {prettyValue(parsed)}
    </pre>
  );
}

const FileToolCard: React.FC<ToolCallCardProps> = ({ toolCall }) => {
  const [previewExpanded, setPreviewExpanded] = useState(false);
  const { action, target } = buildFileToolTitle(toolCall);
  const statusColor = getStatusColor(toolCall.status);
  const secondary = buildFileToolSecondary(toolCall);
  const isSummaryOnlyTool = toolCall.toolName === "ls" || toolCall.toolName === "glob";
  const isCompactPreviewTool = toolCall.toolName === "ls" || toolCall.toolName === "glob";
  const previewLines = (
    isSummaryOnlyTool
      ? []
      : isCompactPreviewTool
      ? getSearchCollectionEntries(toolCall.output)
      : buildFileToolPreview(toolCall)
  ).filter(Boolean);
  const canTogglePreview = isCompactPreviewTool && previewLines.length > 3;
  const visiblePreviewLines =
    canTogglePreview && !previewExpanded ? previewLines.slice(0, 3) : previewLines;
  const previewOverflow = isCompactPreviewTool
    ? Math.max(previewLines.length - visiblePreviewLines.length, 0)
    : getFileToolPreviewOverflow(toolCall, previewLines);
  const useLightPreviewSurface = SEARCH_FILE_TOOL_NAMES.has(toolCall.toolName);
  const searchInputLines = SEARCH_FILE_TOOL_NAMES.has(toolCall.toolName)
    ? buildSearchInputLines(toolCall)
    : [];

  return (
    <div
      style={{
        position: "relative",
        marginBottom: 12,
        paddingLeft: 22,
      }}
    >
      <div
        style={{
          position: "absolute",
          left: 6,
          top: 10,
          bottom: 0,
          width: 1,
          background: "rgba(34, 197, 94, 0.2)",
        }}
      />
      <div
        style={{
          position: "absolute",
          left: 2,
          top: 9,
          width: 9,
          height: 9,
          borderRadius: "50%",
          background: statusColor,
          boxShadow: `0 0 0 4px ${toolCall.status === "failed" ? "rgba(255,77,79,0.12)" : "rgba(34,197,94,0.12)"}`,
        }}
      />

      <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", marginBottom: 6 }}>
        <span
          style={{
            color: statusColor,
            display: "inline-flex",
            alignItems: "center",
            opacity: 0.92,
          }}
        >
          {getFileToolIcon(toolCall.toolName)}
        </span>
        <Text strong style={{ color: "#1f1f1f", fontSize: 15 }}>
          {action}
        </Text>
        {target && (
          <Text
            code
            style={{
              margin: 0,
              padding: 0,
              background: "transparent",
              color: "#0958d9",
              fontSize: 13,
            }}
          >
            {target}
          </Text>
        )}
        {isSummaryOnlyTool && secondary && (
          <Text
            style={{
              color: "#595959",
              fontSize: 13,
            }}
          >
            {secondary}
          </Text>
        )}
        <Tag color={toolCall.status === "success" ? "success" : toolCall.status === "failed" ? "error" : "processing"} style={{ textTransform: "lowercase" }}>
          {getStatusLabel(toolCall.status)}
        </Tag>
      </div>

      {!isSummaryOnlyTool && searchInputLines.length > 0 && (
        <div
          style={{
            marginBottom: secondary || previewLines.length > 0 ? 8 : 0,
            padding: "8px 10px",
            borderRadius: 8,
            background: "#f8fafc",
            border: "1px solid #e2e8f0",
          }}
        >
          <div
            style={{
              marginBottom: 4,
              color: "#64748b",
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: 0.3,
              textTransform: "uppercase",
            }}
          >
            Input
          </div>
          {searchInputLines.map((line, index) => (
            <div
              key={`${toolCall.id}-input-${index}`}
              style={{
                color: "#334155",
                fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace",
                fontSize: 12,
                lineHeight: 1.6,
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {line}
            </div>
          ))}
        </div>
      )}

      {!isSummaryOnlyTool && secondary && (
        <Paragraph
          style={{
            marginBottom: previewLines.length > 0 ? 8 : 0,
            color: "#595959",
            whiteSpace: "pre-wrap",
            fontSize: 13,
          }}
        >
          {secondary}
        </Paragraph>
      )}

      {visiblePreviewLines.length > 0 && (
        <div
          style={{
            padding: "10px 12px",
            borderRadius: 10,
            background: useLightPreviewSurface ? "#f8fafc" : "#0f1720",
            border: useLightPreviewSurface
              ? "1px solid #e2e8f0"
              : "1px solid rgba(15, 23, 32, 0.08)",
          }}
        >
          {visiblePreviewLines.map((line, index) => (
            <div
              key={`${toolCall.id}-preview-${index}`}
              style={{
                color: useLightPreviewSurface ? "#334155" : "#e5e7eb",
                fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace",
                fontSize: 12,
                lineHeight: 1.6,
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {line}
            </div>
          ))}
          {previewOverflow > 0 && (
            <div
              style={{
                marginTop: 6,
                color: useLightPreviewSurface ? "#64748b" : "#94a3b8",
                fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace",
                fontSize: 12,
              }}
            >
              ... {previewOverflow} more
            </div>
          )}
          {canTogglePreview && (
            <button
              type="button"
              onClick={() => setPreviewExpanded((value) => !value)}
              style={{
                marginTop: 8,
                padding: 0,
                border: "none",
                background: "transparent",
                color: "#1677ff",
                cursor: "pointer",
                fontSize: 12,
                fontWeight: 500,
              }}
            >
              {previewExpanded ? "收起" : "展开"}
            </button>
          )}
        </div>
      )}

      {toolCall.error && (
        <Paragraph type="danger" style={{ marginTop: 8, marginBottom: 0, whiteSpace: "pre-wrap", fontSize: 13 }}>
          {normalizeTextPaths(toolCall.error)}
        </Paragraph>
      )}
    </div>
  );
};

const ToolCallCard: React.FC<ToolCallCardProps> = ({ toolCall }) => {
  if (FILE_TOOL_NAMES.has(toolCall.toolName)) {
    return <FileToolCard toolCall={toolCall} />;
  }

  const summary = summarizeToolInput(toolCall);

  const icon =
    toolCall.status === "running" ? (
      <LoadingOutlined style={{ color: "#1677ff" }} />
    ) : toolCall.status === "success" ? (
      <CheckCircleOutlined style={{ color: "#52c41a" }} />
    ) : toolCall.status === "failed" ? (
      <CloseCircleOutlined style={{ color: "#ff4d4f" }} />
    ) : (
      <ToolOutlined />
    );

  const outputView =
    toolCall.toolName === "web_search" || toolCall.toolName === "fetch_url" ? (
      renderWebOutput(toolCall.output)
    ) : (
      <pre
        style={{
          margin: 0,
          padding: 12,
          background: "#fafafa",
          borderRadius: 8,
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          overflowX: "auto",
        }}
      >
        {prettyValue(parseMaybeJson(toolCall.output))}
      </pre>
    );

  return (
    <Card
      size="small"
      style={{
        marginBottom: 10,
        borderRadius: 12,
        borderColor: toolCall.status === "failed" ? "#ffccc7" : "#d9f2e6",
        background: toolCall.status === "failed" ? "#fff2f0" : "#f8fffb",
      }}
      bodyStyle={{ padding: 14 }}
    >
      <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: summary ? 8 : 0 }}>
        {icon}
        <Text strong>{toolCall.toolName}</Text>
        <Tag
          color={toolCall.status === "success" ? "success" : toolCall.status === "failed" ? "error" : "processing"}
          style={{ textTransform: "lowercase" }}
        >
          {getStatusLabel(toolCall.status)}
        </Tag>
        {toolCall.duration != null && (
          <Text type="secondary" style={{ marginLeft: "auto", fontSize: 12 }}>
            {toolCall.duration.toFixed(2)}s
          </Text>
        )}
      </div>

      {summary && (
        <Text type="secondary" style={{ display: "block", marginBottom: 10 }}>
          {summary}
        </Text>
      )}

      <Collapse
        ghost
        items={[
          {
            key: "details",
            label: "Details",
            children: (
              <div style={{ display: "grid", gap: 14 }}>
                <div>
                  <Text strong style={{ display: "block", marginBottom: 6 }}>
                    Input
                  </Text>
                  <pre
                    style={{
                      margin: 0,
                      padding: 12,
                      background: "#fafafa",
                      borderRadius: 8,
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                      overflowX: "auto",
                    }}
                  >
                    {prettyValue(toolCall.input)}
                  </pre>
                </div>

                {toolCall.output !== undefined && toolCall.output !== null && (
                  <div>
                    <Text strong style={{ display: "block", marginBottom: 6 }}>
                      Output
                    </Text>
                    {outputView}
                  </div>
                )}

                {toolCall.error && (
                  <div>
                    <Text strong type="danger" style={{ display: "block", marginBottom: 6 }}>
                      Error
                    </Text>
                    <Paragraph
                      type="danger"
                      style={{
                        marginBottom: 0,
                        padding: 12,
                        borderRadius: 8,
                        background: "#fff1f0",
                        whiteSpace: "pre-wrap",
                      }}
                    >
                      {normalizeTextPaths(toolCall.error)}
                    </Paragraph>
                  </div>
                )}
              </div>
            ),
          },
        ]}
      />
    </Card>
  );
};

export default ToolCallCard;
