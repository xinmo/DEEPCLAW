import { useState, useEffect, useRef, useCallback } from "react";
import { Card, Button, Select, Space, Typography, Tag, message } from "antd";
import { Play, Square, Monitor, MonitorOff, Clock, Zap, MessageSquare, Loader } from "lucide-react";
import { startCompanion, stopCompanion, getCompanionStatus } from "../../services/translateApi";
import type { VoiceInfo, WSMessage, SubtitleEntry } from "../../types/translate";

const { Text } = Typography;

interface Props {
  voices: VoiceInfo[];
  sendJson: (msg: WSMessage) => void;
  connected: boolean;
  subtitles: SubtitleEntry[];
  companionConnected?: boolean;
}

export default function MeetingMode({
  voices,
  sendJson,
  connected,
  subtitles,
}: Props) {
  const [voiceId, setVoiceId] = useState("");
  const [running, setRunning] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [latency, setLatency] = useState<number | null>(null);
  const [companionRunning, setCompanionRunning] = useState(false);
  const [starting, setStarting] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval>>(undefined);
  const subtitleEndRef = useRef<HTMLDivElement | null>(null);

  const checkCompanionStatus = useCallback(async () => {
    try {
      const status = await getCompanionStatus();
      setCompanionRunning(status.running);
    } catch {
      setCompanionRunning(false);
    }
  }, []);

  useEffect(() => {
    checkCompanionStatus();
    const interval = setInterval(checkCompanionStatus, 5000);
    return () => clearInterval(interval);
  }, [checkCompanionStatus]);

  useEffect(() => {
    if (running) {
      setElapsed(0);
      timerRef.current = setInterval(() => setElapsed((t) => t + 1), 1000);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [running]);

  useEffect(() => {
    subtitleEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [subtitles]);

  useEffect(() => {
    if (subtitles.length >= 2) {
      const recent = subtitles.filter((s) => s.is_final).slice(-4);
      if (recent.length >= 2) {
        for (let i = recent.length - 1; i >= 1; i--) {
          if (recent[i].type === "translation" && recent[i - 1].type === "transcript") {
            setLatency(recent[i].timestamp - recent[i - 1].timestamp);
            break;
          }
        }
      }
    }
  }, [subtitles]);

  const formatElapsed = (s: number) => {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    if (h > 0) return `${h}:${m.toString().padStart(2, "0")}:${sec.toString().padStart(2, "0")}`;
    return `${m.toString().padStart(2, "0")}:${sec.toString().padStart(2, "0")}`;
  };

  // 开始翻译：自动启动伴侣（如果未运行）
  const handleStart = async () => {
    if (!voiceId) return;
    setStarting(true);

    try {
      // 检查伴侣状态，未运行则自动启动
      if (!companionRunning) {
        message.loading({ content: "正在启动桌面伴侣...", key: "companion" });
        await startCompanion(voiceId);
        setCompanionRunning(true);
        message.success({ content: "桌面伴侣已启动", key: "companion" });
      }

      // 启动翻译
      sendJson({ type: "meeting_start", data: { voice_id: voiceId } });
      setRunning(true);
      setLatency(null);
    } catch (e) {
      console.error("Failed to start:", e);
      message.error({ content: "启动失败，请检查桌面伴侣是否正确安装", key: "companion" });
    } finally {
      setStarting(false);
    }
  };

  // 停止翻译：同时停止伴侣
  const handleStop = async () => {
    sendJson({ type: "meeting_stop", data: {} });
    setRunning(false);

    // 停止伴侣
    try {
      await stopCompanion();
      setCompanionRunning(false);
    } catch (e) {
      console.error("Failed to stop companion:", e);
    }
  };

  const getSubtitleColor = (type: string) => {
    switch (type) {
      case "transcript": return "blue";
      case "translation": return "green";
      case "user_transcript": return "orange";
      default: return "default";
    }
  };

  const getSubtitleLabel = (type: string) => {
    switch (type) {
      case "transcript": return "EN";
      case "translation": return "ZH";
      case "user_transcript": return "ME";
      default: return "";
    }
  };

  return (
    <Card className="translate-card" title="会议翻译模式">
      <Space direction="vertical" style={{ width: "100%" }} size="middle">
        <Text type="secondary" style={{ fontSize: 13 }}>
          需安装 VB-Cable，腾讯会议麦克风选择 "CABLE Output"
        </Text>

        {/* Voice selection */}
        <div className="translate-input">
          <Select
            style={{ width: "100%" }}
            size="large"
            placeholder="选择你的克隆声音..."
            value={voiceId || undefined}
            onChange={setVoiceId}
            disabled={running || starting}
            showSearch
            filterOption={(input, option) =>
              (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
            }
            options={voices.map((v) => ({ label: v.name, value: v.voice_id }))}
            notFoundContent="未找到匹配的声音"
          />
        </div>

        {/* Control buttons with companion status tag */}
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {running ? (
            <Button
              danger
              size="large"
              icon={<Square size={18} />}
              onClick={handleStop}
              style={{ cursor: "pointer", height: 48, paddingInline: 32, borderRadius: 8 }}
            >
              停止翻译
            </Button>
          ) : (
            <Button
              type="primary"
              size="large"
              icon={<Play size={18} />}
              onClick={handleStart}
              loading={starting}
              disabled={!voiceId || !connected}
              style={{
                cursor: !voiceId || !connected ? "not-allowed" : "pointer",
                height: 48,
                paddingInline: 32,
                background: voiceId && connected ? "#2563EB" : undefined,
                borderColor: voiceId && connected ? "#2563EB" : undefined,
                borderRadius: 8,
                fontWeight: 500
              }}
            >
              开始翻译
            </Button>
          )}
          {/* 伴侣状态小标签 */}
          <Tag
            color={companionRunning ? "success" : "default"}
            icon={companionRunning ? <Monitor size={12} /> : <MonitorOff size={12} />}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 4,
              padding: "4px 8px",
              margin: 0
            }}
          >
            {companionRunning ? "伴侣就绪" : "伴侣待启动"}
          </Tag>
        </div>

        {/* Dashboard */}
        {running && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
            <div className="stats-card">
              <div style={{ color: "#10B981", marginBottom: 8 }}><Loader size={20} className="animate-spin" /></div>
              <div className="stats-label">状态</div>
              <div className="stats-value" style={{ fontSize: 16, color: "#10B981" }}>翻译中</div>
            </div>
            <div className="stats-card">
              <div style={{ color: "#3B82F6", marginBottom: 8 }}><Clock size={20} /></div>
              <div className="stats-label">时长</div>
              <div className="stats-value">{formatElapsed(elapsed)}</div>
            </div>
            <div className="stats-card">
              <div style={{ color: latency && latency > 2000 ? "#F59E0B" : "#3B82F6", marginBottom: 8 }}><Zap size={20} /></div>
              <div className="stats-label">延迟</div>
              <div className="stats-value" style={{ color: latency && latency > 2000 ? "#F59E0B" : undefined }}>
                {latency ? `${latency}ms` : "--"}
              </div>
            </div>
            <div className="stats-card">
              <div style={{ color: "#3B82F6", marginBottom: 8 }}><MessageSquare size={20} /></div>
              <div className="stats-label">字幕数</div>
              <div className="stats-value">{subtitles.filter(s => s.is_final).length}</div>
            </div>
          </div>
        )}

        {/* Subtitles */}
        <Card
          className="translate-card"
          size="small"
          title={
            <Space>
              <span style={{ fontWeight: 600 }}>实时字幕</span>
              <Tag color="blue">EN 英文原文</Tag>
              <Tag color="green">ZH 中文翻译</Tag>
              <Tag color="orange">ME 你说的</Tag>
            </Space>
          }
        >
          <div className="subtitle-panel">
            {subtitles.length === 0 && !running && (
              <Text type="secondary" style={{ display: "block", textAlign: "center", padding: 24 }}>
                选择声音后点击"开始翻译"
              </Text>
            )}
            {subtitles.length === 0 && running && (
              <Text type="secondary" style={{ display: "block", textAlign: "center", padding: 24 }}>
                等待语音输入...
              </Text>
            )}
            {subtitles.map((s, i) => (
              <div key={`${s.timestamp}-${i}`} className={`subtitle-item ${s.type} ${s.is_final ? "final" : "partial"}`}>
                <Tag color={getSubtitleColor(s.type)} style={{ minWidth: 36, textAlign: "center" }}>
                  {getSubtitleLabel(s.type)}
                </Tag>
                <Text style={{ flex: 1 }}>{s.text}</Text>
                {s.is_final && (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {new Date(s.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                  </Text>
                )}
              </div>
            ))}
            <div ref={subtitleEndRef} />
          </div>
        </Card>
      </Space>
    </Card>
  );
}
