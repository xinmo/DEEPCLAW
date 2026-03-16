import React, { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Divider,
  Grid,
  Input,
  Space,
  Switch,
  Tag,
  Typography,
  message,
} from "antd";

import { channelApi } from "../services/channelApi";
import type {
  ChannelSummary,
  QQChannelConfigPayload,
  QQChannelDetail,
} from "../types/channel";

const { useBreakpoint } = Grid;
const { Paragraph, Text, Title } = Typography;
const { TextArea } = Input;

interface ChannelsPageProps {
  initialChannel?: string;
}

const STATUS_COLOR_MAP: Record<string, string> = {
  running: "green",
  starting: "blue",
  stopped: "default",
  disabled: "default",
  error: "red",
  unavailable: "orange",
};

function normalizeAllowList(rawValue: string): string[] {
  return rawValue
    .replace(/,/g, "\n")
    .split("\n")
    .map((item) => item.trim())
    .filter((item, index, items) => item.length > 0 && items.indexOf(item) === index);
}

const ChannelsPage: React.FC<ChannelsPageProps> = ({ initialChannel = "qq" }) => {
  const screens = useBreakpoint();
  const isNarrowLayout = !screens.lg;
  const [channels, setChannels] = useState<ChannelSummary[]>([]);
  const [selectedChannel, setSelectedChannel] = useState(initialChannel);
  const [qqDetail, setQqDetail] = useState<QQChannelDetail | null>(null);
  const [formState, setFormState] = useState<QQChannelConfigPayload>({
    enabled: false,
    app_id: "",
    secret: "",
    allow_from: [],
  });
  const [allowListText, setAllowListText] = useState("");
  const [loadingList, setLoadingList] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [saving, setSaving] = useState(false);

  const loadChannels = async () => {
    try {
      setLoadingList(true);
      const data = await channelApi.listChannels();
      setChannels(data.channels);
      if (data.channels.length > 0 && !data.channels.some((channel) => channel.name === selectedChannel)) {
        setSelectedChannel(data.channels[0].name);
      }
    } catch (error) {
      message.error("加载渠道列表失败");
      console.error(error);
    } finally {
      setLoadingList(false);
    }
  };

  const loadQQDetail = async () => {
    try {
      setLoadingDetail(true);
      const detail = await channelApi.getQQChannel();
      setQqDetail(detail);
      setFormState(detail.config);
      setAllowListText(detail.config.allow_from.join("\n"));
    } catch (error) {
      message.error("加载 QQ 渠道配置失败");
      console.error(error);
    } finally {
      setLoadingDetail(false);
    }
  };

  useEffect(() => {
    const initialize = async () => {
      try {
        setLoadingList(true);
        const data = await channelApi.listChannels();
        setChannels(data.channels);
        if (data.channels.length > 0) {
          setSelectedChannel((current) => {
            if (data.channels.some((channel) => channel.name === current)) {
              return current;
            }
            return data.channels[0].name;
          });
        }
      } catch (error) {
        message.error("加载渠道列表失败");
        console.error(error);
      } finally {
        setLoadingList(false);
      }
    };

    void initialize();
  }, []);

  useEffect(() => {
    if (selectedChannel !== "qq") {
      return;
    }

    const initialize = async () => {
      try {
        setLoadingDetail(true);
        const detail = await channelApi.getQQChannel();
        setQqDetail(detail);
        setFormState(detail.config);
        setAllowListText(detail.config.allow_from.join("\n"));
      } catch (error) {
        message.error("加载 QQ 渠道配置失败");
        console.error(error);
      } finally {
        setLoadingDetail(false);
      }
    };

    void initialize();
  }, [selectedChannel]);

  const handleSave = async () => {
    try {
      setSaving(true);
      const nextPayload: QQChannelConfigPayload = {
        ...formState,
        allow_from: normalizeAllowList(allowListText),
      };
      const detail = await channelApi.updateQQChannel(nextPayload);
      setQqDetail(detail);
      setFormState(detail.config);
      setAllowListText(detail.config.allow_from.join("\n"));
      message.success("QQ 渠道配置已保存");
      await loadChannels();
    } catch (error) {
      message.error("保存 QQ 渠道配置失败");
      console.error(error);
    } finally {
      setSaving(false);
    }
  };

  const runtime = qqDetail?.runtime;
  const allowListPreview = normalizeAllowList(allowListText);

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: isNarrowLayout ? "minmax(0, 1fr)" : "320px minmax(0, 1fr)",
        gap: 24,
        alignItems: "start",
      }}
    >
      <div
        style={{
          minWidth: 0,
          border: "1px solid #f0f0f0",
          borderRadius: 12,
          overflow: "hidden",
          background: "#fafafa",
        }}
      >
        <div style={{ padding: 16, borderBottom: "1px solid #f0f0f0" }}>
          <Title level={5} style={{ margin: 0 }}>
            渠道
          </Title>
          <Text type="secondary">
            统一管理外部消息渠道。当前先接入 QQ，后续可以继续扩展到更多渠道。
          </Text>
        </div>
        <div style={{ padding: 12, display: "flex", flexDirection: "column", gap: 10 }}>
          {channels.map((channel) => {
            const selected = channel.name === selectedChannel;
            return (
              <button
                key={channel.name}
                type="button"
                onClick={() => setSelectedChannel(channel.name)}
                style={{
                  width: "100%",
                  textAlign: "left",
                  padding: "14px 16px",
                  borderRadius: 10,
                  appearance: "none",
                  border: selected ? "1px solid #91caff" : "1px solid transparent",
                  background: selected ? "#e6f4ff" : "#fff",
                  fontFamily: "inherit",
                  cursor: "pointer",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: 12,
                  }}
                >
                  <Text strong>{channel.label}</Text>
                  <Tag color={channel.enabled ? "green" : "default"}>
                    {channel.enabled ? "已启用" : "已停用"}
                  </Tag>
                </div>
                <Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
                  {channel.status_message}
                </Paragraph>
                <Space wrap size={[8, 8]} style={{ marginTop: 12 }}>
                  <Tag color={channel.configured ? "blue" : "default"}>
                    {channel.configured ? "已配置" : "未配置"}
                  </Tag>
                  <Tag color={STATUS_COLOR_MAP[channel.status] || "default"}>{channel.status}</Tag>
                </Space>
              </button>
            );
          })}
          {!loadingList && channels.length === 0 ? (
            <Text type="secondary">当前还没有可配置的渠道。</Text>
          ) : null}
        </div>
      </div>

      <div
        style={{
          minWidth: 0,
          border: "1px solid #f0f0f0",
          borderRadius: 12,
          background: "#fff",
          padding: isNarrowLayout ? 16 : 24,
        }}
      >
        <Space direction="vertical" size="large" style={{ width: "100%" }}>
          <div>
            <Title level={4} style={{ marginTop: 0, marginBottom: 8 }}>
              QQ 渠道接入
            </Title>
            <Paragraph type="secondary" style={{ marginBottom: 0, maxWidth: 880 }}>
              这里配置从 nanobot 迁移过来的 QQ 渠道参数。保存后，后端会按最新配置自动重载 QQ 渠道。
            </Paragraph>
          </div>

          {runtime ? (
            <Card
              size="small"
              title="运行状态"
              extra={
                <Space wrap size={[8, 8]}>
                  <Tag color={qqDetail?.configured ? "blue" : "default"}>
                    {qqDetail?.configured ? "已配置" : "未配置"}
                  </Tag>
                  <Tag color={STATUS_COLOR_MAP[runtime.state] || "default"}>{runtime.state}</Tag>
                </Space>
              }
            >
              <Space direction="vertical" size="small" style={{ width: "100%" }}>
                <Text>{runtime.message}</Text>
                <Space wrap size={[8, 8]}>
                  <Tag color={runtime.installed ? "green" : "orange"}>
                    {runtime.installed ? "QQ SDK 已安装" : "缺少 QQ SDK"}
                  </Tag>
                  <Tag color={runtime.available ? "green" : "default"}>
                    {runtime.available ? "可用" : "不可用"}
                  </Tag>
                  <Tag color={runtime.running ? "green" : "default"}>
                    {runtime.running ? "运行中" : "未运行"}
                  </Tag>
                </Space>
              </Space>
            </Card>
          ) : null}

          {!runtime?.installed ? (
            <Alert
              type="warning"
              showIcon
              message="当前环境缺少 QQ SDK"
              description="页面配置仍然可以保存，但只有安装 qq-botpy 后，QQ 渠道才能真正启动。"
            />
          ) : null}

          {qqDetail && qqDetail.validation_errors.length > 0 ? (
            <Alert
              type="error"
              showIcon
              message="当前配置还不能启动 QQ 渠道"
              description={
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {qqDetail.validation_errors.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              }
            />
          ) : null}

          <div>
            <Text strong>启用渠道</Text>
            <Divider style={{ margin: "8px 0 16px" }} />
            <Switch
              checked={formState.enabled}
              checkedChildren="启用"
              unCheckedChildren="停用"
              onChange={(checked) => setFormState((current) => ({ ...current, enabled: checked }))}
            />
            <Paragraph type="secondary" style={{ marginTop: 12, marginBottom: 0 }}>
              启用后，后端会根据已保存的配置尝试启动 QQ 机器人。
            </Paragraph>
          </div>

          <div>
            <Text strong>接入参数</Text>
            <Divider style={{ margin: "8px 0 16px" }} />
            <Space direction="vertical" size="middle" style={{ width: "100%" }}>
              <div>
                <Text>App ID</Text>
                <Input
                  value={formState.app_id}
                  onChange={(event) =>
                    setFormState((current) => ({ ...current, app_id: event.target.value }))
                  }
                  placeholder="请输入 QQ 开放平台提供的 App ID"
                />
              </div>
              <div>
                <Text>App Secret</Text>
                <Input.Password
                  value={formState.secret}
                  onChange={(event) =>
                    setFormState((current) => ({ ...current, secret: event.target.value }))
                  }
                  placeholder="请输入 QQ 开放平台提供的 App Secret"
                />
              </div>
              <div>
                <Text>允许接入用户</Text>
                <TextArea
                  value={allowListText}
                  onChange={(event) => setAllowListText(event.target.value)}
                  autoSize={{ minRows: 4, maxRows: 8 }}
                  placeholder={
                    "每行一个用户 openid，用于限制只有白名单用户可以触发机器人\nuser_openid_1\nuser_openid_2"
                  }
                />
                <Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
                  这个字段复用 nanobot 的 allow_from 配置，用来限制 QQ 频道里的 openid 白名单。
                </Paragraph>
              </div>
            </Space>
          </div>

          <div>
            <Text strong>白名单预览</Text>
            <Divider style={{ margin: "8px 0 16px" }} />
            <Space wrap size={[8, 8]}>
              {allowListPreview.length > 0 ? (
                allowListPreview.map((item) => <Tag key={item}>{item}</Tag>)
              ) : (
                <Text type="secondary">未填写白名单，表示允许所有 QQ 用户触发。</Text>
              )}
            </Space>
          </div>

          <Space>
            <Button type="primary" onClick={() => void handleSave()} loading={saving || loadingDetail}>
              保存配置
            </Button>
            <Button onClick={() => void loadQQDetail()} loading={loadingDetail}>
              重新加载
            </Button>
          </Space>
        </Space>
      </div>
    </div>
  );
};

export default ChannelsPage;
