from pydantic import BaseModel
from typing import Optional


class CloneResponse(BaseModel):
    voice_id: str
    name: str


class VoiceInfo(BaseModel):
    voice_id: str
    name: str
    preview_url: Optional[str] = None


class WSMessageType:
    TTS_REQUEST = "tts_request"
    MEETING_START = "meeting_start"
    MEETING_STOP = "meeting_stop"
    TTS_AUDIO = "tts_audio"
    TTS_DONE = "tts_done"
    SUBTITLE = "subtitle"
    STATUS = "status"
    ERROR = "error"
