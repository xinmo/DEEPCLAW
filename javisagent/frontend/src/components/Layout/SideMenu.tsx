import React, { useState } from "react";
import { Layout, Menu } from "antd";
import {
  Bot,
  ChevronLeft,
  ChevronRight,
  Cog,
  Database,
  FileText,
  FlaskConical,
  FolderOpen,
  Languages,
  MessageSquare,
  Mic,
  Plug,
  Settings,
  User,
} from "lucide-react";

const { Sider } = Layout;

const LABELS = {
  smartParse: "\u667a\u80fd\u89e3\u6790",
  documentParse: "\u6587\u6863\u89e3\u6790",
  smartTranslate: "\u667a\u80fd\u7ffb\u8bd1",
  realtimeTranslate: "\u5b9e\u65f6\u7ffb\u8bd1",
  smartKnowledge: "\u667a\u80fd\u77e5\u8bc6",
  knowledgeBase: "\u77e5\u8bc6\u5e93",
  knowledgeChat: "\u77e5\u8bc6\u95ee\u7b54",
  chat: "\u5bf9\u8bdd",
  promptManagement: "Prompt \u7ba1\u7406",
  skillManagement: "\u6280\u80fd\u7ba1\u7406",
  channelAccess: "\u6e20\u9053\u63a5\u5165",
  mcpManagement: "MCP \u7ba1\u7406",
  aiResearch: "AI\u7814\u7a76\u9662",
  industryResearch: "\u4ea7\u4e1a\u7814\u7a76\u5ba4",
  settings: "\u8bbe\u7f6e",
  accountSettings: "\u8d26\u6237\u8bbe\u7f6e",
  systemSettings: "\u7cfb\u7edf\u8bbe\u7f6e",
};

interface SideMenuProps {
  onMenuSelect?: (key: string) => void;
  selectedKey?: string;
}

const SideMenu: React.FC<SideMenuProps> = ({
  onMenuSelect,
  selectedKey = "document-parse",
}) => {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <Sider
      width={200}
      collapsed={collapsed}
      collapsedWidth={64}
      style={{ background: "#fff", borderRight: "1px solid #f0f0f0" }}
      trigger={null}
    >
      <div
        style={{
          padding: collapsed ? "16px 8px" : "16px",
          fontSize: collapsed ? "14px" : "18px",
          fontWeight: "bold",
          color: "#1890ff",
          display: "flex",
          alignItems: "center",
          justifyContent: collapsed ? "center" : "flex-start",
          height: "64px",
          borderBottom: "1px solid #f0f0f0",
        }}
      >
        {!collapsed && "JAVISAGENT"}
      </div>

      <Menu
        mode="inline"
        selectedKeys={[selectedKey]}
        defaultOpenKeys={["smart-parse", "smart-translate", "smart-knowledge", "claw", "ai-research"]}
        style={{ height: "calc(100% - 64px)", borderRight: 0 }}
        onClick={({ key }) => onMenuSelect?.(key)}
        items={[
          {
            key: "smart-parse",
            label: collapsed ? "" : LABELS.smartParse,
            icon: <FileText size={16} />,
            children: [
              {
                key: "document-parse",
                label: collapsed ? "" : LABELS.documentParse,
                icon: <FileText size={16} />,
              },
            ],
          },
          {
            key: "smart-translate",
            label: collapsed ? "" : LABELS.smartTranslate,
            icon: <Languages size={16} />,
            children: [
              {
                key: "realtime-translate",
                label: collapsed ? "" : LABELS.realtimeTranslate,
                icon: <Mic size={16} />,
              },
            ],
          },
          {
            key: "smart-knowledge",
            label: collapsed ? "" : LABELS.smartKnowledge,
            icon: <Database size={16} />,
            children: [
              {
                key: "knowledge-base",
                label: collapsed ? "" : LABELS.knowledgeBase,
                icon: <FolderOpen size={16} />,
              },
              {
                key: "knowledge-chat",
                label: collapsed ? "" : LABELS.knowledgeChat,
                icon: <MessageSquare size={16} />,
              },
            ],
          },
          {
            key: "claw",
            label: collapsed ? "" : "Claw",
            icon: <Bot size={16} />,
            children: [
              {
                key: "claw-chat",
                label: collapsed ? "" : LABELS.chat,
                icon: <MessageSquare size={16} />,
              },
              {
                key: "prompt-management",
                label: collapsed ? "" : LABELS.promptManagement,
                icon: <FileText size={16} />,
              },
              {
                key: "claw-skills",
                label: collapsed ? "" : LABELS.skillManagement,
                icon: <Cog size={16} />,
              },
              {
                key: "channel-qq",
                label: collapsed ? "" : LABELS.channelAccess,
                icon: <Plug size={16} />,
              },
              {
                key: "mcp-management",
                label: collapsed ? "" : LABELS.mcpManagement,
                icon: <Plug size={16} />,
              },
            ],
          },
          {
            key: "ai-research",
            label: collapsed ? "" : LABELS.aiResearch,
            icon: <FlaskConical size={16} />,
            children: [
              {
                key: "industry-research",
                label: collapsed ? "" : LABELS.industryResearch,
                icon: <FlaskConical size={16} />,
              },
            ],
          },
          {
            key: "settings",
            label: collapsed ? "" : LABELS.settings,
            icon: <Settings size={16} />,
            children: [
              {
                key: "account-settings",
                label: collapsed ? "" : LABELS.accountSettings,
                icon: <User size={16} />,
              },
              {
                key: "system-settings",
                label: collapsed ? "" : LABELS.systemSettings,
                icon: <Cog size={16} />,
              },
            ],
          },
        ]}
      />

      <div
        style={{
          position: "absolute",
          right: -12,
          top: "50%",
          transform: "translateY(-50%)",
          width: 24,
          height: 24,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#fff",
          borderRadius: "50%",
          boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
          cursor: "pointer",
          zIndex: 10,
        }}
        onClick={() => setCollapsed(!collapsed)}
      >
        {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </div>
    </Sider>
  );
};

export default SideMenu;
