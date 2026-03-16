import { useState, useRef, useEffect, useCallback } from "react";
import { Card, Button, Input, Upload, message, Progress, List, Space, Typography, Steps } from "antd";
import { Upload as UploadIcon, Mic, MicOff, Trash2, Copy, CheckCircle, Edit3 } from "lucide-react";
import { cloneVoice, deleteVoice } from "../../services/translateApi";
import type { VoiceInfo } from "../../types/translate";

const { Text } = Typography;

interface Props {
  voices: VoiceInfo[];
  onVoicesChange: () => void;
}

// 从文件名提取默认名称（去掉扩展名）
const getDefaultName = (filename: string): string => {
  const lastDot = filename.lastIndexOf(".");
  return lastDot > 0 ? filename.substring(0, lastDot) : filename;
};

export default function VoiceClone({ voices, onVoicesChange }: Props) {
  const [name, setName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [recording, setRecording] = useState(false);
  const [recordTime, setRecordTime] = useState(0);
  const [cloneProgress, setCloneProgress] = useState(0);
  const [isEditingName, setIsEditingName] = useState(false);

  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval>>(undefined);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animFrameRef = useRef<number>(0);
  const audioCtxRef = useRef<AudioContext | null>(null);

  // 计算当前步骤
  const currentStep = !file ? 0 : 1;

  useEffect(() => {
    if (recording) {
      setRecordTime(0);
      timerRef.current = setInterval(() => setRecordTime((t) => t + 1), 1000);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [recording]);

  const drawWaveform = useCallback(() => {
    const canvas = canvasRef.current;
    const analyser = analyserRef.current;
    if (!canvas || !analyser) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const bufLen = analyser.frequencyBinCount;
    const data = new Uint8Array(bufLen);
    analyser.getByteTimeDomainData(data);

    // 渐变背景
    const gradient = ctx.createLinearGradient(0, 0, canvas.width, 0);
    gradient.addColorStop(0, "#1E293B");
    gradient.addColorStop(1, "#334155");
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // 波形线条
    ctx.lineWidth = 2;
    ctx.strokeStyle = "#3B82F6";
    ctx.beginPath();

    const sliceW = canvas.width / bufLen;
    let x = 0;
    for (let i = 0; i < bufLen; i++) {
      const v = data[i] / 128.0;
      const y = (v * canvas.height) / 2;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
      x += sliceW;
    }
    ctx.lineTo(canvas.width, canvas.height / 2);
    ctx.stroke();

    if (recording) {
      animFrameRef.current = requestAnimationFrame(drawWaveform);
    }
  }, [recording]);

  useEffect(() => {
    if (recording) {
      animFrameRef.current = requestAnimationFrame(drawWaveform);
    }
    return () => cancelAnimationFrame(animFrameRef.current);
  }, [recording, drawWaveform]);

  const formatTime = (s: number) =>
    `${Math.floor(s / 60).toString().padStart(2, "0")}:${(s % 60).toString().padStart(2, "0")}`;

  const handleUpload = async () => {
    if (!file) {
      message.error("请先选择或录制音频文件");
      return;
    }
    // 如果没有手动输入名称，使用默认名称
    const voiceName = name.trim() || getDefaultName(file.name);
    if (!voiceName) {
      message.error("请输入声音名称");
      return;
    }
    setLoading(true);
    setCloneProgress(10);

    const progressTimer = setInterval(() => {
      setCloneProgress((p) => (p >= 90 ? 90 : p + 10));
    }, 800);

    try {
      await cloneVoice(voiceName, file);
      clearInterval(progressTimer);
      setCloneProgress(100);
      message.success(`"${voiceName}" 克隆成功`);
      setName("");
      setFile(null);
      setIsEditingName(false);
      onVoicesChange();
      setTimeout(() => setCloneProgress(0), 2000);
    } catch (e: unknown) {
      clearInterval(progressTimer);
      setCloneProgress(0);
      message.error((e as Error).message || "克隆失败");
    } finally {
      setLoading(false);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const audioCtx = new AudioContext();
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 2048;
      source.connect(analyser);
      analyserRef.current = analyser;
      audioCtxRef.current = audioCtx;

      const recorder = new MediaRecorder(stream);
      chunks.current = [];
      recorder.ondataavailable = (e) => chunks.current.push(e.data);
      recorder.onstop = () => {
        const blob = new Blob(chunks.current, { type: "audio/wav" });
        const timestamp = new Date().toLocaleString("zh-CN", {
          month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit"
        }).replace(/[/:]/g, "-");
        const defaultRecordingName = `录音_${timestamp}`;
        const f = new File([blob], `${defaultRecordingName}.wav`, { type: "audio/wav" });
        setFile(f);
        // 自动设置录音的默认名称
        if (!name) {
          setName(defaultRecordingName);
        }
        stream.getTracks().forEach((t) => t.stop());
        audioCtx.close();
        analyserRef.current = null;
        audioCtxRef.current = null;
      };
      recorder.start();
      mediaRecorder.current = recorder;
      setRecording(true);
    } catch {
      message.error("无法访问麦克风");
    }
  };

  const stopRecording = () => {
    mediaRecorder.current?.stop();
    setRecording(false);
  };

  const handleDelete = async (voiceId: string) => {
    try {
      await deleteVoice(voiceId);
      message.success("删除成功");
      onVoicesChange();
    } catch (e: unknown) {
      message.error((e as Error).message);
    }
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      message.success("ID 已复制到剪贴板");
    } catch {
      message.error("复制失败");
    }
  };

  return (
    <Card className="translate-card" title="声音克隆" style={{ marginBottom: 16 }}>
      {/* 步骤指示器 */}
      <Steps
        current={currentStep}
        size="small"
        style={{ marginBottom: 24 }}
        items={[
          { title: "选择音频", description: "上传或录制" },
          { title: "确认克隆", description: "检查名称" },
        ]}
      />

      <Text type="secondary" style={{ display: "block", marginBottom: 16 }}>
        上传或录制至少15秒的音频来克隆声音
      </Text>

      <Space direction="vertical" style={{ width: "100%" }} size="middle">
        {/* 步骤1: 选择音频 */}
        <Space>
          <Upload
            beforeUpload={(f) => {
              setFile(f);
              // 自动填充文件名作为默认名称
              if (!name) {
                setName(getDefaultName(f.name));
              }
              return false;
            }}
            showUploadList={false}
            accept="audio/*"
            disabled={loading || recording}
          >
            <Button icon={<UploadIcon size={16} />} style={{ cursor: "pointer" }}>选择音频文件</Button>
          </Upload>

          {recording ? (
            <Button danger icon={<MicOff size={16} />} onClick={stopRecording} style={{ cursor: "pointer" }}>
              停止录制
            </Button>
          ) : (
            <Button icon={<Mic size={16} />} onClick={startRecording} disabled={loading} style={{ cursor: "pointer" }}>
              录制音频
            </Button>
          )}
        </Space>

        {recording && (
          <div className="waveform-container">
            <canvas ref={canvasRef} width={400} height={60} className="waveform-canvas" />
            <Space style={{ marginTop: 12 }}>
              <span className="recording-indicator">
                <span className="recording-dot" />
                录制中
              </span>
              <span style={{ color: "#FFFFFF", fontWeight: 500 }}>{formatTime(recordTime)}</span>
              {recordTime < 15 ? (
                <span style={{ color: "#F59E0B" }}>还需 {15 - recordTime} 秒</span>
              ) : (
                <span style={{ color: "#10B981" }}>时长足够</span>
              )}
            </Space>
          </div>
        )}

        {/* 步骤2: 已选择文件，显示名称编辑 */}
        {file && !recording && (
          <div
            style={{
              padding: 16,
              backgroundColor: "#f0fdf4",
              borderRadius: 8,
              border: "1px solid #86efac"
            }}
          >
            <Space direction="vertical" style={{ width: "100%" }} size="small">
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <CheckCircle size={18} style={{ color: "#22c55e" }} />
                <Text strong>已选择: {file.name}</Text>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8 }}>
                <Text type="secondary">声音名称:</Text>
                {isEditingName ? (
                  <Input
                    size="small"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    onBlur={() => setIsEditingName(false)}
                    onPressEnter={() => setIsEditingName(false)}
                    autoFocus
                    style={{ width: 200 }}
                    placeholder="输入声音名称"
                  />
                ) : (
                  <Space>
                    <Text strong style={{ color: "#1890ff" }}>
                      {name || getDefaultName(file.name)}
                    </Text>
                    <Button
                      type="text"
                      size="small"
                      icon={<Edit3 size={14} />}
                      onClick={() => setIsEditingName(true)}
                      style={{ cursor: "pointer" }}
                    >
                      修改
                    </Button>
                  </Space>
                )}
              </div>
            </Space>
          </div>
        )}

        {cloneProgress > 0 && (
          <Progress
            className="translate-progress"
            percent={cloneProgress}
            status={cloneProgress === 100 ? "success" : "active"}
          />
        )}

        {cloneProgress === 0 && (
          <Button
            type="primary"
            onClick={handleUpload}
            disabled={loading || !file}
            style={{
              cursor: loading || !file ? "not-allowed" : "pointer",
              background: file ? "#2563EB" : undefined,
              borderColor: file ? "#2563EB" : undefined,
              height: 40,
              borderRadius: 8,
              fontWeight: 500
            }}
          >
            {file ? "开始克隆" : "请先选择音频"}
          </Button>
        )}
      </Space>

      {voices.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <Text strong style={{ fontSize: 15 }}>已克隆的声音 ({voices.length})</Text>
          <List
            style={{ marginTop: 12 }}
            dataSource={voices}
            renderItem={(v) => (
              <div className="voice-list-item">
                <List.Item
                  style={{ border: "none", padding: 0 }}
                  actions={[
                    <Button
                      key="copy"
                      size="small"
                      icon={<Copy size={14} />}
                      onClick={() => copyToClipboard(v.voice_id)}
                      style={{ cursor: "pointer" }}
                    >
                      复制ID
                    </Button>,
                    <Button
                      key="delete"
                      size="small"
                      danger
                      icon={<Trash2 size={14} />}
                      onClick={() => handleDelete(v.voice_id)}
                      style={{ cursor: "pointer" }}
                    >
                      删除
                    </Button>
                  ]}
                >
                  <List.Item.Meta
                    title={<span style={{ fontWeight: 600 }}>{v.name}</span>}
                    description={<Text type="secondary" copyable={{ text: v.voice_id }}>{v.voice_id.slice(0, 20)}...</Text>}
                  />
                </List.Item>
              </div>
            )}
          />
        </div>
      )}
    </Card>
  );
}
