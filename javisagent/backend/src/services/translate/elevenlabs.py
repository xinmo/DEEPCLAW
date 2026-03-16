import httpx
import json
import logging
from typing import AsyncGenerator

from .config import get_translate_settings

logger = logging.getLogger(__name__)
settings = get_translate_settings()


class ElevenLabsService:
    """ElevenLabs API integration for voice cloning and streaming TTS."""

    def __init__(self):
        self.base_url = settings.elevenlabs_base_url
        self.ws_url = settings.elevenlabs_ws_url
        self.api_key = settings.elevenlabs_api_key
        self.headers = {"xi-api-key": self.api_key}

    # ── Voice Cloning ──

    async def clone_voice(
        self, name: str, audio_data: bytes, description: str = "", filename: str = "sample.mp3"
    ) -> dict:
        """Clone a voice from audio data. Returns {voice_id, name}."""
        mime_map = {
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".m4a": "audio/mp4",
            ".ogg": "audio/ogg",
            ".webm": "audio/webm",
        }
        ext = "." + filename.rsplit(".", 1)[-1] if "." in filename else ".mp3"
        mime_type = mime_map.get(ext.lower(), "audio/mpeg")

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/voices/add",
                headers=self.headers,
                data={"name": name, "description": description},
                files={"files": (filename, audio_data, mime_type)},
            )
            if resp.status_code != 200:
                try:
                    error_detail = resp.json()
                    logger.error(f"ElevenLabs API error: {error_detail}")
                    raise Exception(f"ElevenLabs error: {error_detail.get('detail', {}).get('message', str(error_detail))}")
                except Exception as e:
                    if "ElevenLabs error" in str(e):
                        raise
                    raise Exception(f"ElevenLabs API returned {resp.status_code}: {resp.text}")
            data = resp.json()
            return {"voice_id": data["voice_id"], "name": name}

    async def list_voices(self) -> list[dict]:
        """List all available voices."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}/voices", headers=self.headers
            )
            resp.raise_for_status()
            voices = resp.json().get("voices", [])
            return [
                {
                    "voice_id": v["voice_id"],
                    "name": v["name"],
                    "preview_url": v.get("preview_url"),
                }
                for v in voices
            ]

    async def delete_voice(self, voice_id: str) -> bool:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.delete(
                f"{self.base_url}/voices/{voice_id}",
                headers=self.headers,
            )
            return resp.status_code == 200

    # ── Streaming TTS ──

    async def stream_tts(
        self, text: str, voice_id: str
    ) -> AsyncGenerator[bytes, None]:
        """Stream TTS audio via WebSocket. Yields PCM audio chunks."""
        import websockets
        import base64

        url = (
            f"{self.ws_url}/text-to-speech/{voice_id}/stream-input"
            f"?model_id={settings.elevenlabs_tts_model}"
            f"&output_format=pcm_16000"
        )

        async with websockets.connect(
            url, additional_headers=self.headers
        ) as ws:
            # Send initial config
            await ws.send(json.dumps({
                "text": " ",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                },
            }))

            # Send the text
            await ws.send(json.dumps({"text": text}))

            # Signal end of input
            await ws.send(json.dumps({"text": ""}))

            # Receive audio chunks
            async for message in ws:
                if isinstance(message, str):
                    data = json.loads(message)
                    if data.get("audio"):
                        yield base64.b64decode(data["audio"])
                    if data.get("isFinal"):
                        break
                elif isinstance(message, bytes):
                    yield message

    async def open_tts_stream(self, voice_id: str):
        """Open a persistent TTS WebSocket for meeting mode."""
        import websockets

        url = (
            f"{self.ws_url}/text-to-speech/{voice_id}/stream-input"
            f"?model_id={settings.elevenlabs_tts_model}"
            f"&output_format=pcm_16000"
        )
        ws = await websockets.connect(
            url, additional_headers=self.headers
        )
        # Send initial config
        await ws.send(json.dumps({
            "text": " ",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        }))
        return ws

    async def close_tts_stream(self, ws_connection):
        """Close a TTS WebSocket by sending flush and closing."""
        try:
            await ws_connection.send(json.dumps({"text": ""}))
            await ws_connection.close()
        except Exception:
            pass
