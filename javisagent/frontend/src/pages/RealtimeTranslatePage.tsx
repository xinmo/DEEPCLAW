import { useState, useEffect, useCallback } from "react";
import { Tabs } from "antd";
import { Mic, Volume2, Users, Wifi, WifiOff } from "lucide-react";
import VoiceClone from "../components/Translate/VoiceClone";
import TextToSpeech from "../components/Translate/TextToSpeech";
import MeetingMode from "../components/Translate/MeetingMode";
import { useWebSocket } from "../hooks/useWebSocket";
import { useAudioPlayer } from "../hooks/useAudioPlayer";
import { listVoices } from "../services/translateApi";
import type { VoiceInfo, WSMessage, SubtitleEntry } from "../types/translate";
import "../styles/translate.css";

export default function RealtimeTranslatePage() {
  const [voices, setVoices] = useState<VoiceInfo[]>([]);
  const [subtitles, setSubtitles] = useState<SubtitleEntry[]>([]);
  const [companionConnected, setCompanionConnected] = useState(false);
  const { playChunk, stop: stopAudio } = useAudioPlayer();

  const handleWSMessage = useCallback(
    (msg: WSMessage) => {
      switch (msg.type) {
        case "tts_audio":
          if (msg.data.source === "tts") {
            playChunk(msg.data.audio as string);
          }
          break;
        case "tts_done":
          break;
        case "subtitle":
          setSubtitles((prev) => {
            const entryData = msg.data as { type: SubtitleEntry['type']; text: string; is_final: boolean; lang: SubtitleEntry['lang'] };
            const entry: SubtitleEntry = {
              type: entryData.type,
              text: entryData.text,
              is_final: entryData.is_final,
              lang: entryData.lang,
              timestamp: Date.now(),
            };
            if (entry.is_final) {
              const filtered = prev.filter((s) => !(s.type === entry.type && !s.is_final));
              return [...filtered, entry].slice(-50);
            }
            // 使用 findIndex 从后往前查找替代 findLastIndex
            let idx = -1;
            for (let i = prev.length - 1; i >= 0; i--) {
              if (prev[i].type === entry.type && !prev[i].is_final) {
                idx = i;
                break;
              }
            }
            if (idx >= 0) {
              const copy = [...prev];
              copy[idx] = entry;
              return copy;
            }
            return [...prev, entry].slice(-50);
          });
          break;
        case "status": {
          const state = msg.data.state as string;
          if (state === "companion_connected") {
            setCompanionConnected(true);
          } else if (state === "companion_disconnected") {
            setCompanionConnected(false);
          }
          break;
        }
        case "error":
          console.error("WS Error:", msg.data.message);
          break;
      }
    },
    [playChunk]
  );

  const { connected, sendJson } = useWebSocket(handleWSMessage);

  const refreshVoices = useCallback(async () => {
    try {
      const v = await listVoices();
      // 反转列表，让最新克隆的排在最上面
      setVoices(v.reverse());
    } catch {
      // silent on initial load
    }
  }, []);

  useEffect(() => {
    refreshVoices();
  }, [refreshVoices]);

  const tabItems = [
    {
      key: "clone",
      label: (
        <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Mic size={18} />
          声音克隆
        </span>
      ),
      children: <VoiceClone voices={voices} onVoicesChange={refreshVoices} />,
    },
    {
      key: "tts",
      label: (
        <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Volume2 size={18} />
          文字转语音
        </span>
      ),
      children: <TextToSpeech voices={voices} sendJson={sendJson} connected={connected} />,
    },
    {
      key: "meeting",
      label: (
        <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Users size={18} />
          会议翻译
        </span>
      ),
      children: (
        <MeetingMode
          voices={voices}
          sendJson={sendJson}
          connected={connected}
          subtitles={subtitles}
          companionConnected={companionConnected}
        />
      ),
    },
  ];

  return (
    <div className="translate-page">
      {/* 页面头部 */}
      <div className="translate-header">
        <div>
          <h2 className="translate-header-title">实时翻译</h2>
          <p className="translate-header-subtitle">中英实时翻译 · 语音克隆 · 会议同传</p>
        </div>
        <div className={`connection-badge ${connected ? "connected" : "disconnected"}`}>
          <span className="connection-dot" />
          {connected ? <Wifi size={16} /> : <WifiOff size={16} />}
          {connected ? "服务已连接" : "服务未连接"}
        </div>
      </div>

      {/* Tab 内容 */}
      <Tabs
        className="translate-tabs"
        defaultActiveKey="clone"
        items={tabItems}
        onChange={(key) => {
          if (key === "tts") stopAudio();
        }}
      />
    </div>
  );
}
