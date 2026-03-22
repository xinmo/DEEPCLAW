import React, { useEffect, useState } from "react";
import {
  Button,
  Card,
  Drawer,
  Empty,
  Grid,
  Input,
  Modal,
  Popconfirm,
  Space,
  Tag,
  Typography,
  message,
} from "antd";
import { DeleteOutlined, PlusOutlined, SaveOutlined } from "@ant-design/icons";

import { clawApi } from "../services/clawApi";
import type { MCPConfig, MCPServerConfig } from "../types/claw";

const { useBreakpoint } = Grid;
const { Text, Title, Paragraph } = Typography;
const { TextArea } = Input;

const DEFAULT_STDIO_TEMPLATE: MCPServerConfig = {
  type: "stdio",
  command: "",
  args: [],
  env: {},
};

const DEFAULT_SSE_TEMPLATE: MCPServerConfig = {
  type: "sse",
  url: "",
  headers: {},
};

function getTransportBadge(config: MCPServerConfig) {
  const t = config.type ?? config.transport ?? "stdio";
  const colorMap: Record<string, string> = {
    stdio: "blue",
    sse: "green",
    http: "purple",
  };
  return <Tag color={colorMap[t as string] ?? "default"}>{String(t).toUpperCase()}</Tag>;
}

const ClawMcpPage: React.FC = () => {
  const screens = useBreakpoint();
  const isNarrowLayout = !screens.xl;

  const [config, setConfig] = useState<MCPConfig>({ mcpServers: {} });
  const [selectedName, setSelectedName] = useState<string>("");
  const [editJson, setEditJson] = useState<string>("");
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [detailDrawerOpen, setDetailDrawerOpen] = useState(false);

  // 新增服务器 Modal
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [newServerName, setNewServerName] = useState("");
  const [newServerType, setNewServerType] = useState<"stdio" | "sse">("stdio");

  // 导入完整配置 Modal
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [importJson, setImportJson] = useState("");
  const [importError, setImportError] = useState<string | null>(null);

  useEffect(() => {
    void loadConfig();
  }, []);

  useEffect(() => {
    if (!selectedName) {
      setEditJson("");
      setJsonError(null);
      return;
    }
    const serverConfig = config.mcpServers[selectedName];
    if (serverConfig !== undefined) {
      setEditJson(JSON.stringify(serverConfig, null, 2));
      setJsonError(null);
    }
  }, [selectedName, config]);

  const loadConfig = async () => {
    try {
      setLoading(true);
      const data = await clawApi.getMcpConfig();
      setConfig(data);
      // 如果有服务器且没有选中，自动选第一个
      const names = Object.keys(data.mcpServers);
      if (names.length > 0 && !selectedName) {
        setSelectedName(names[0]);
      }
    } catch (err) {
      void message.error("加载 MCP 配置失败");
    } finally {
      setLoading(false);
    }
  };

  const handleSelectServer = (name: string) => {
    setSelectedName(name);
    if (isNarrowLayout) {
      setDetailDrawerOpen(true);
    }
  };

  const handleJsonChange = (value: string) => {
    setEditJson(value);
    try {
      JSON.parse(value);
      setJsonError(null);
    } catch {
      setJsonError("JSON 格式错误");
    }
  };

  const handleSaveServer = async () => {
    if (!selectedName) return;
    if (jsonError) {
      void message.error("请修复 JSON 格式错误后再保存");
      return;
    }
    let parsed: MCPServerConfig;
    try {
      parsed = JSON.parse(editJson) as MCPServerConfig;
    } catch {
      void message.error("JSON 解析失败");
      return;
    }
    const newConfig: MCPConfig = {
      mcpServers: { ...config.mcpServers, [selectedName]: parsed },
    };
    try {
      setSaving(true);
      await clawApi.saveMcpConfig(newConfig);
      setConfig(newConfig);
      void message.success("配置已保存");
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : String(err);
      void message.error(`保存失败: ${errMsg}`);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteServer = async (name: string) => {
    const newServers = { ...config.mcpServers };
    delete newServers[name];
    const newConfig: MCPConfig = { mcpServers: newServers };
    try {
      await clawApi.saveMcpConfig(newConfig);
      setConfig(newConfig);
      if (selectedName === name) {
        const remaining = Object.keys(newServers);
        setSelectedName(remaining[0] ?? "");
      }
      void message.success(`已删除服务器 "${name}"`);
    } catch (err) {
      void message.error("删除失败");
    }
  };

  const handleImportConfig = async () => {
    let parsed: unknown;
    try {
      parsed = JSON.parse(importJson);
    } catch {
      setImportError("JSON 格式错误，请检查后重试");
      return;
    }
    // 支持两种格式：完整配置 {mcpServers: {...}} 或直接是 servers 对象
    let servers: Record<string, unknown>;
    if (
      parsed !== null &&
      typeof parsed === "object" &&
      "mcpServers" in (parsed as object) &&
      typeof (parsed as { mcpServers: unknown }).mcpServers === "object"
    ) {
      servers = (parsed as { mcpServers: Record<string, unknown> }).mcpServers;
    } else if (parsed !== null && typeof parsed === "object") {
      servers = parsed as Record<string, unknown>;
    } else {
      setImportError("格式不正确，请粘贴完整的 MCP 配置 JSON");
      return;
    }
    const newConfig: MCPConfig = {
      mcpServers: { ...config.mcpServers, ...(servers as MCPConfig["mcpServers"]) },
    };
    try {
      await clawApi.saveMcpConfig(newConfig);
      setConfig(newConfig);
      const names = Object.keys(servers);
      if (names.length > 0) setSelectedName(names[0]);
      setImportModalOpen(false);
      setImportJson("");
      setImportError(null);
      void message.success(`已导入 ${names.length} 个服务器配置`);
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : String(err);
      setImportError(`保存失败: ${errMsg}`);
    }
  };

  const handleAddServer = async () => {
    const trimmed = newServerName.trim();
    if (!trimmed) {
      void message.error("请输入服务器名称");
      return;
    }
    if (config.mcpServers[trimmed] !== undefined) {
      void message.error(`服务器 "${trimmed}" 已存在`);
      return;
    }
    const template = newServerType === "sse" ? DEFAULT_SSE_TEMPLATE : DEFAULT_STDIO_TEMPLATE;
    const newConfig: MCPConfig = {
      mcpServers: { ...config.mcpServers, [trimmed]: { ...template } },
    };
    try {
      await clawApi.saveMcpConfig(newConfig);
      setConfig(newConfig);
      setSelectedName(trimmed);
      setAddModalOpen(false);
      setNewServerName("");
      setNewServerType("stdio");
      void message.success(`已添加服务器 "${trimmed}"`);
    } catch (err) {
      void message.error("添加失败");
    }
  };

  const serverNames = Object.keys(config.mcpServers);

  const renderDetail = () => {
    if (!selectedName) {
      return (
        <Empty
          description={serverNames.length === 0 ? "暂无 MCP 服务器，点击右上角添加" : "请在左侧选择一个服务器"}
          style={{ marginTop: 60 }}
        />
      );
    }
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 16, height: "100%" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <Title level={5} style={{ margin: 0 }}>{selectedName}</Title>
            {config.mcpServers[selectedName] && (
              <div style={{ marginTop: 4 }}>{getTransportBadge(config.mcpServers[selectedName])}</div>
            )}
          </div>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            onClick={() => void handleSaveServer()}
            loading={saving}
            disabled={!!jsonError}
          >
            保存
          </Button>
        </div>

        {jsonError && (
          <Text type="danger" style={{ fontSize: 12 }}>{jsonError}</Text>
        )}

        <TextArea
          value={editJson}
          onChange={(e) => handleJsonChange(e.target.value)}
          style={{
            fontFamily: "monospace",
            fontSize: 13,
            flex: 1,
            minHeight: 400,
            borderColor: jsonError ? "#ff4d4f" : undefined,
          }}
          autoSize={{ minRows: 16 }}
        />

        <Paragraph type="secondary" style={{ fontSize: 12, margin: 0 }}>
          支持的类型：<Text code>stdio</Text>（本地进程，需 command 字段）、
          <Text code>sse</Text> / <Text code>http</Text>（远程服务，需 url 字段）。
          修改后点击「保存」生效，下次 Claw 对话时自动加载。
        </Paragraph>
      </div>
    );
  };

  return (
    <>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: isNarrowLayout ? "1fr" : "280px 1fr",
          gap: 16,
          height: "calc(100vh - 32px)",
          padding: 16,
          boxSizing: "border-box",
        }}
      >
        {/* 左侧服务器列表 */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 12,
            overflowY: "auto",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <Title level={5} style={{ margin: 0 }}>MCP 服务器列表</Title>
            <Space size={4}>
              <Button
                size="small"
                onClick={() => { setImportJson(""); setImportError(null); setImportModalOpen(true); }}
              >
                导入
              </Button>
              <Button
                type="primary"
                size="small"
                icon={<PlusOutlined />}
                onClick={() => setAddModalOpen(true)}
              >
                添加
              </Button>
            </Space>
          </div>

          {serverNames.length === 0 ? (
            <Empty description="暂无配置" style={{ marginTop: 40 }} />
          ) : (
            serverNames.map((name) => {
              const srv = config.mcpServers[name];
              const isSelected = name === selectedName;
              return (
                <Card
                  key={name}
                  size="small"
                  hoverable
                  onClick={() => handleSelectServer(name)}
                  style={{
                    cursor: "pointer",
                    borderColor: isSelected ? "#1890ff" : undefined,
                    background: isSelected ? "#e6f4ff" : undefined,
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <Text strong ellipsis style={{ display: "block" }}>{name}</Text>
                      <div style={{ marginTop: 4 }}>{getTransportBadge(srv)}</div>
                      {(srv.command ?? srv.url) && (
                        <Text type="secondary" style={{ fontSize: 11, display: "block", marginTop: 4 }} ellipsis>
                          {srv.command ?? srv.url}
                        </Text>
                      )}
                    </div>
                    <Popconfirm
                      title={`确定删除服务器 "${name}" 吗？`}
                      onConfirm={(e) => { e?.stopPropagation(); void handleDeleteServer(name); }}
                      onCancel={(e) => e?.stopPropagation()}
                      okText="删除"
                      cancelText="取消"
                      okButtonProps={{ danger: true }}
                    >
                      <Button
                        size="small"
                        type="text"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={(e) => e.stopPropagation()}
                        style={{ marginLeft: 8, flexShrink: 0 }}
                      />
                    </Popconfirm>
                  </div>
                </Card>
              );
            })
          )}
        </div>

        {/* 右侧详情（宽屏） */}
        {!isNarrowLayout && (
          <div
            style={{
              border: "1px solid #f0f0f0",
              borderRadius: 12,
              background: "#fff",
              padding: 24,
              overflowY: "auto",
            }}
          >
            {renderDetail()}
          </div>
        )}
      </div>

      {/* 窄屏：Drawer */}
      {isNarrowLayout && (
        <Drawer
          title={selectedName || "服务器配置"}
          placement="right"
          width="100%"
          open={detailDrawerOpen}
          onClose={() => setDetailDrawerOpen(false)}
        >
          {renderDetail()}
        </Drawer>
      )}

      {/* 添加服务器 Modal */}
      <Modal
        title="添加 MCP 服务器"
        open={addModalOpen}
        onOk={() => void handleAddServer()}
        onCancel={() => { setAddModalOpen(false); setNewServerName(""); setNewServerType("stdio"); }}
        okText="添加"
        cancelText="取消"
      >
        <Space direction="vertical" style={{ width: "100%" }} size={12}>
          <div>
            <Text>服务器名称</Text>
            <Input
              style={{ marginTop: 4 }}
              placeholder="例如: filesystem、my-api"
              value={newServerName}
              onChange={(e) => setNewServerName(e.target.value)}
              onPressEnter={() => void handleAddServer()}
            />
          </div>
          <div>
            <Text>传输类型</Text>
            <div style={{ marginTop: 4, display: "flex", gap: 8 }}>
              <Button
                type={newServerType === "stdio" ? "primary" : "default"}
                onClick={() => setNewServerType("stdio")}
              >
                stdio（本地进程）
              </Button>
              <Button
                type={newServerType === "sse" ? "primary" : "default"}
                onClick={() => setNewServerType("sse")}
              >
                sse/http（远程）
              </Button>
            </div>
          </div>
          <Text type="secondary" style={{ fontSize: 12 }}>
            添加后可在右侧编辑器中填写完整配置。
          </Text>
        </Space>
      </Modal>

      {/* 导入完整配置 Modal */}
      <Modal
        title="导入 MCP 配置"
        open={importModalOpen}
        onOk={() => void handleImportConfig()}
        onCancel={() => setImportModalOpen(false)}
        okText="导入"
        cancelText="取消"
        width={560}
      >
        <Space direction="vertical" style={{ width: "100%" }} size={12}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            粘贴完整的 MCP 配置 JSON，支持 <Text code>&#123;"mcpServers": &#123;...&#125;&#125;</Text> 格式。
            导入的服务器将合并到现有配置中。
          </Text>
          <TextArea
            value={importJson}
            onChange={(e) => { setImportJson(e.target.value); setImportError(null); }}
            placeholder={'&#123;\n  "mcpServers": &#123;\n    "my-server": &#123; "type": "http", "url": "https://..." &#125;\n  &#125;\n&#125;'}
            style={{ fontFamily: "monospace", fontSize: 13, minHeight: 200 }}
            autoSize={{ minRows: 10 }}
          />
          {importError && <Text type="danger" style={{ fontSize: 12 }}>{importError}</Text>}
        </Space>
      </Modal>
    </>
  );
};

export default ClawMcpPage;
