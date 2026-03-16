import json
import logging
import base64
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.services.translate import ElevenLabsService, MeetingSession
from src.schemas.translate import WSMessageType

logger = logging.getLogger(__name__)
router = APIRouter()
elevenlabs = ElevenLabsService()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """Main WebSocket endpoint for TTS and meeting mode."""
    await ws.accept()
    logger.info("WebSocket client connected")

    meeting_session: MeetingSession | None = None

    async def send_json(msg_type: str, data: dict):
        await ws.send_json({"type": msg_type, "data": data})

    async def on_subtitle(data: dict):
        await send_json(WSMessageType.SUBTITLE, data)

    async def on_outbound_audio(audio_chunk: bytes):
        await ws.send_json({
            "type": WSMessageType.TTS_AUDIO,
            "data": {
                "audio": base64.b64encode(audio_chunk).decode(),
                "source": "meeting_outbound",
            },
        })

    async def on_status(data: dict):
        await send_json(WSMessageType.STATUS, data)

    try:
        while True:
            raw = await ws.receive()

            if raw.get("type") == "websocket.disconnect":
                logger.info("WebSocket disconnect message received")
                break

            # Handle binary audio frames from companion
            if "bytes" in raw and raw["bytes"]:
                if meeting_session and meeting_session.is_running:
                    data = raw["bytes"]
                    # First byte indicates stream: 0=meeting, 1=mic
                    stream_id = data[0]
                    audio = data[1:]
                    if stream_id == 0:
                        await meeting_session.feed_meeting_audio(audio)
                    elif stream_id == 1:
                        await meeting_session.feed_mic_audio(audio)
                continue

            # Handle JSON text messages
            if "text" in raw and raw["text"]:
                msg = json.loads(raw["text"])
                msg_type = msg.get("type")
                msg_data = msg.get("data", {})

                if msg_type == WSMessageType.TTS_REQUEST:
                    await handle_tts(ws, msg_data)

                elif msg_type == WSMessageType.MEETING_START:
                    if meeting_session:
                        await meeting_session.stop()
                    meeting_session = MeetingSession(
                        voice_id=msg_data["voice_id"],
                        on_subtitle=on_subtitle,
                        on_outbound_audio=on_outbound_audio,
                        on_status=on_status,
                    )
                    await meeting_session.start()

                elif msg_type == WSMessageType.MEETING_STOP:
                    if meeting_session:
                        await meeting_session.stop()
                        meeting_session = None

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if meeting_session:
            await meeting_session.stop()


async def handle_tts(ws: WebSocket, data: dict):
    """Handle a text-to-speech request."""
    text = data.get("text", "")
    voice_id = data.get("voice_id", "")

    if not text or not voice_id:
        await ws.send_json({
            "type": WSMessageType.ERROR,
            "data": {"message": "text and voice_id required"},
        })
        return

    try:
        async for audio_chunk in elevenlabs.stream_tts(text, voice_id):
            await ws.send_json({
                "type": WSMessageType.TTS_AUDIO,
                "data": {
                    "audio": base64.b64encode(audio_chunk).decode(),
                    "source": "tts",
                },
            })
        await ws.send_json({
            "type": WSMessageType.TTS_DONE,
            "data": {},
        })
    except Exception as e:
        logger.error(f"TTS error: {e}")
        await ws.send_json({
            "type": WSMessageType.ERROR,
            "data": {"message": f"TTS failed: {str(e)}"},
        })
