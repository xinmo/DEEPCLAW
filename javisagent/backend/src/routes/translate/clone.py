import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from src.services.translate import ElevenLabsService
from src.schemas.translate import CloneResponse, VoiceInfo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["voices"])
elevenlabs = ElevenLabsService()


@router.post("/clone", response_model=CloneResponse)
async def clone_voice(
    name: str = Form(...),
    description: str = Form(""),
    file: UploadFile = File(...),
):
    """Upload audio to clone a voice."""
    audio_data = await file.read()
    if len(audio_data) < 1000:
        raise HTTPException(400, "Audio file too small. Need at least 15 seconds.")

    try:
        result = await elevenlabs.clone_voice(name, audio_data, description, file.filename or "sample.mp3")
        return CloneResponse(**result)
    except Exception as e:
        logger.error(f"Clone failed: {e}")
        raise HTTPException(500, f"Voice cloning failed: {str(e)}")


@router.get("/voices", response_model=list[VoiceInfo])
async def list_voices():
    """List all available cloned voices."""
    try:
        voices = await elevenlabs.list_voices()
        return [VoiceInfo(**v) for v in voices]
    except Exception as e:
        logger.error(f"List voices failed: {e}")
        raise HTTPException(500, str(e))


@router.delete("/voices/{voice_id}")
async def delete_voice(voice_id: str):
    """Delete a cloned voice."""
    ok = await elevenlabs.delete_voice(voice_id)
    if not ok:
        raise HTTPException(404, "Voice not found")
    return {"status": "deleted"}
