import { useState, useRef } from "react";
import { Card, Button, Select, Input, Space, Typography } from "antd";
import { Volume2, X, Clock, AlertCircle } from "lucide-react";
import type { VoiceInfo, WSMessage } from "../../types/translate";

const { TextArea } = Input;
const { Text } = Typography;

interface HistoryItem {
  text: string;
  voiceName: string;
  timestamp: number;
}

interface Props {
  voices: VoiceInfo[];
  sendJson: (msg: WSMessage) => void;
  connected: boolean;
}

export default function TextToSpeech({ voices, sendJson, connected }: Props) {
  const [text, setText] = useState("");
  const [voiceId, setVoiceId] = useState("");
  const [generating, setGenerating] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const textRef = useRef("");

  const handleGenerate = () => {
    if (!text || !voiceId) return;
    setGenerating(true);
    textRef.current = text;
    sendJson({
      type: "tts_request",
      data: { text, voice_id: voiceId },
    });

    const voiceName = voices.find((v) => v.voice_id === voiceId)?.name || "";
    setHistory((prev) => [{ text, voiceName, timestamp: Date.now() }, ...prev].slice(0, 20));

    // Reset generating state after a delay (in real app, this would be triggered by WS response)
    setTimeout(() => setGenerating(false), 3000);
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return `${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}`;
  };

  const replayFromHistory = (item: HistoryItem) => {
    const voice = voices.find((v) => v.name === item.voiceName);
    if (voice) {
      setText(item.text);
      setVoiceId(voice.voice_id);
    }
  };

  return (
    <Card className="translate-card" title="文字转语音" style={{ marginBottom: 16 }}>
      <Text type="secondary" style={{ display: "block", marginBottom: 16 }}>
        选择克隆的声音，输入文字生成语音
      </Text>

      <Space direction="vertical" style={{ width: "100%" }} size="middle">
        <div className="translate-input">
          <Select
            style={{ width: "100%" }}
            size="large"
            placeholder="选择声音..."
            value={voiceId || undefined}
            onChange={setVoiceId}
            disabled={generating}
            showSearch
            filterOption={(input, option) =>
              (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
            }
            options={voices.map((v) => ({ label: v.name, value: v.voice_id }))}
            notFoundContent="未找到匹配的声音"
          />
        </div>

        <div className="translate-input">
          <TextArea
            rows={4}
            placeholder="输入要转换的文字..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={generating}
            showCount
            maxLength={5000}
            style={{ borderRadius: 8 }}
          />
        </div>

        <Space>
          <Button
            type="primary"
            icon={<Volume2 size={16} />}
            onClick={handleGenerate}
            loading={generating}
            disabled={!text || !voiceId || !connected}
            style={{
              cursor: !text || !voiceId || !connected ? "not-allowed" : "pointer",
              background: text && voiceId && connected ? "#2563EB" : undefined,
              borderColor: text && voiceId && connected ? "#2563EB" : undefined,
              height: 40,
              borderRadius: 8,
              fontWeight: 500
            }}
          >
            {generating ? "生成中..." : "生成语音"}
          </Button>
          {text && (
            <Button
              icon={<X size={16} />}
              onClick={() => setText("")}
              disabled={generating}
              style={{ cursor: generating ? "not-allowed" : "pointer" }}
            >
              清空
            </Button>
          )}
        </Space>

        {!connected && (
          <div className="status-indicator error">
            <AlertCircle size={16} />
            未连接到服务器
          </div>
        )}

        {history.length > 0 && (
          <Card className="translate-card" size="small" title="生成历史">
            <div style={{ maxHeight: 300, overflowY: "auto" }}>
              {history.map((item, i) => (
                <div
                  key={`${item.timestamp}-${i}`}
                  className="voice-list-item"
                  onClick={() => replayFromHistory(item)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === "Enter" && replayFromHistory(item)}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                    <Text strong>{item.voiceName}</Text>
                    <Space size={4}>
                      <Clock size={12} style={{ color: "#94A3B8" }} />
                      <Text type="secondary" style={{ fontSize: 12 }}>{formatTime(item.timestamp)}</Text>
                    </Space>
                  </div>
                  <Text type="secondary" style={{ fontSize: 13 }}>
                    {item.text.slice(0, 80)}{item.text.length > 80 ? "..." : ""}
                  </Text>
                </div>
              ))}
            </div>
          </Card>
        )}
      </Space>
    </Card>
  );
}
