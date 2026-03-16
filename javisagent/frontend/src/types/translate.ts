export interface VoiceInfo {
  voice_id: string;
  name: string;
  preview_url?: string;
}

export interface CloneResponse {
  voice_id: string;
  name: string;
}

export type WSMessageType =
  | "tts_request"
  | "meeting_start"
  | "meeting_stop"
  | "tts_audio"
  | "tts_done"
  | "subtitle"
  | "error"
  | "status";

export interface WSMessage {
  type: WSMessageType;
  data: Record<string, unknown>;
}

export interface SubtitleEntry {
  type: "transcript" | "translation" | "user_transcript";
  text: string;
  is_final: boolean;
  lang: "en" | "zh";
  timestamp: number;
}

export interface CompanionStatus {
  running: boolean;
  voice_id: string | null;
  pid: number | null;
}
