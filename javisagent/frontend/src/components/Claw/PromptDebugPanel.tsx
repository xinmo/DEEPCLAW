import React from "react";
import { Tag } from "antd";

import type { PromptDebugLayer, PromptDebugSnapshot } from "../../types/claw";

interface PromptDebugPanelProps {
  snapshot: PromptDebugSnapshot;
}

function formatDebugValue(value: unknown) {
  if (typeof value === "string") {
    return value;
  }
  return JSON.stringify(value ?? null, null, 2);
}

function DebugSection({
  title,
  content,
  extra,
}: {
  title: string;
  content: unknown;
  extra?: React.ReactNode;
}) {
  return (
    <section>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
          marginBottom: 8,
        }}
      >
        <div style={{ fontSize: 12, fontWeight: 600, color: "#262626" }}>{title}</div>
        {extra}
      </div>
      <pre
        style={{
          margin: 0,
          padding: "12px 14px",
          borderRadius: 10,
          background: "#fafafa",
          border: "1px solid #f0f0f0",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          fontSize: 12,
          lineHeight: 1.6,
          color: "#434343",
          overflowX: "auto",
        }}
      >
        {formatDebugValue(content)}
      </pre>
    </section>
  );
}

function PromptLayerSection({ layer }: { layer: PromptDebugLayer }) {
  return (
    <DebugSection
      title={layer.title}
      extra={<Tag style={{ marginInlineEnd: 0 }}>{layer.source}</Tag>}
      content={layer.content}
    />
  );
}

const PromptDebugPanel: React.FC<PromptDebugPanelProps> = ({ snapshot }) => {
  const localContext = snapshot.resolved_state.local_context?.trim();
  const memoryContents = snapshot.resolved_state.memory_contents || {};
  const hasMemoryContents = Object.keys(memoryContents).length > 0;
  const skillsLoaded = snapshot.resolved_state.skills_loaded || [];
  const skillSources = snapshot.resolved_state.skills_source_paths || [];

  return (
    <details
      style={{
        marginTop: 12,
        borderRadius: 12,
        background: "#ffffff",
        border: "1px solid #d9d9d9",
      }}
    >
      <summary
        style={{
          cursor: "pointer",
          padding: "10px 12px",
          fontSize: 12,
          fontWeight: 600,
          color: "#0958d9",
          userSelect: "none",
        }}
      >
        查看全部上下文
      </summary>

      <div
        style={{
          padding: "0 12px 12px",
          display: "flex",
          flexDirection: "column",
          gap: 16,
        }}
      >
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Tag color="blue">{snapshot.conversation.llm_model}</Tag>
          <Tag>{`${snapshot.captured_request.message_count} messages`}</Tag>
          <Tag>{`${snapshot.captured_request.tool_count} tools`}</Tag>
          <Tag>{`${snapshot.prompt_layers.length} prompt layers`}</Tag>
          <Tag>{`${skillsLoaded.length} loaded skills`}</Tag>
          {snapshot.captured_at ? <Tag>{snapshot.captured_at}</Tag> : null}
        </div>

        <DebugSection title="Working Directory" content={snapshot.conversation.working_directory} />

        {snapshot.selected_skill?.name ? (
          <DebugSection title="Selected Skill" content={snapshot.selected_skill} />
        ) : null}

        {snapshot.prompt_layers.length > 0 ? (
          <section style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: "#262626" }}>Prompt Layers</div>
            {snapshot.prompt_layers.map((layer) => (
              <PromptLayerSection key={layer.id} layer={layer} />
            ))}
          </section>
        ) : null}

        <DebugSection
          title="Final System Prompt"
          content={snapshot.captured_request.system_prompt}
        />

        <DebugSection title="Messages Sent To Model" content={snapshot.captured_request.messages} />
        <DebugSection title="Tool Definitions" content={snapshot.captured_request.tools} />

        {localContext ? <DebugSection title="Resolved Local Context" content={localContext} /> : null}

        {hasMemoryContents ? (
          <DebugSection title="Resolved Memory Contents" content={memoryContents} />
        ) : null}

        {skillSources.length > 0 ? (
          <DebugSection title="Skill Source Paths" content={skillSources} />
        ) : null}

        {skillsLoaded.length > 0 ? (
          <DebugSection title="Loaded Skill Metadata" content={skillsLoaded} />
        ) : null}
      </div>
    </details>
  );
};

export default PromptDebugPanel;
