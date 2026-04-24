import React, { useState } from "react";
import { Layout, Menu } from "antd";
import {
  Bot,
  ChevronLeft,
  ChevronRight,
  Cog,
  FileText,
  MessageSquare,
  Plug,
} from "lucide-react";

const { Sider } = Layout;

const LABELS = {
  chat: "\u5bf9\u8bdd",
  promptManagement: "Prompt \u7ba1\u7406",
  skillManagement: "\u6280\u80fd\u7ba1\u7406",
  channelAccess: "\u6e20\u9053\u63a5\u5165",
  mcpManagement: "MCP \u7ba1\u7406",
};

interface SideMenuProps {
  onMenuSelect?: (key: string) => void;
  selectedKey?: string;
}

const SideMenu: React.FC<SideMenuProps> = ({
  onMenuSelect,
  selectedKey = "claw-chat",
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
        {!collapsed && "DEEPCLAW"}
      </div>

      <Menu
        mode="inline"
        selectedKeys={[selectedKey]}
        defaultOpenKeys={["claw"]}
        style={{ height: "calc(100% - 64px)", borderRight: 0 }}
        onClick={({ key }) => onMenuSelect?.(key)}
        items={[
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
