import asyncio
import logging
import time
from typing import Optional, Callable

from .elevenlabs import ElevenLabsService
from .xfyun_asr import XfyunASRService
from .xfyun_translate import XfyunTranslateService
from src.audio.vad import VAD
from src.audio.segmenter import Segmenter

logger = logging.getLogger(__name__)


class MeetingSession:
    """Orchestrates bidirectional translation for a meeting session.

    Inbound:  meeting audio (EN) → iFlytek ASR → iFlytek Translate → Chinese subtitles
    Outbound: user mic (ZH) → iFlytek ASR → iFlytek Translate → ElevenLabs TTS (EN) → VB-Cable
    """

    def __init__(
        self,
        voice_id: str,
        on_subtitle: Callable,
        on_outbound_audio: Callable,
        on_status: Callable,
    ):
        self.voice_id = voice_id
        self.on_subtitle = on_subtitle
        self.on_outbound_audio = on_outbound_audio
        self.on_status = on_status

        self.asr = XfyunASRService()
        self.translator = XfyunTranslateService()
        self.elevenlabs = ElevenLabsService()

        self._inbound_stream = None  # EN ASR
        self._outbound_stream = None  # ZH ASR
        self._tts_ws = None

        self._inbound_vad = VAD(aggressiveness=2)
        self._outbound_vad = VAD(aggressiveness=2)
        self._segmenter = Segmenter()

        self._running = False
        self._tts_queue: asyncio.Queue[str] = asyncio.Queue()
        self._tts_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the meeting translation session."""
        logger.info("Starting meeting session")
        self._running = True

        # Open inbound stream: EN ASR (meeting audio → English transcript)
        self._inbound_stream = await self.asr.create_stream(
            source_lang="en",
            on_transcript=self._on_inbound_transcript,
        )

        # Open outbound stream: ZH ASR (user mic → Chinese transcript)
        self._outbound_stream = await self.asr.create_stream(
            source_lang="zh",
            on_transcript=self._on_outbound_transcript,
        )

        # Open persistent TTS WebSocket
        self._tts_ws = await self.elevenlabs.open_tts_stream(self.voice_id)

        # Start TTS consumer task
        self._tts_task = asyncio.create_task(self._tts_consumer())

        await self.on_status({"state": "running"})
        logger.info("Meeting session started")

    async def stop(self):
        """Stop the meeting session and clean up."""
        logger.info("Stopping meeting session")
        self._running = False

        # Flush remaining text
        remaining = self._segmenter.flush()
        if remaining:
            self._tts_queue.put_nowait(remaining)
        self._tts_queue.put_nowait(None)  # Sentinel

        if self._tts_task:
            await self._tts_task

        tasks = []
        if self._inbound_stream:
            tasks.append(self._inbound_stream.close())
        if self._outbound_stream:
            tasks.append(self._outbound_stream.close())
        if self._tts_ws:
            tasks.append(self.elevenlabs.close_tts_stream(self._tts_ws))
        tasks.append(self.translator.close())

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self._inbound_vad.reset()
        self._outbound_vad.reset()
        self._segmenter.reset()

        await self.on_status({"state": "stopped"})
        logger.info("Meeting session stopped")

    async def feed_meeting_audio(self, audio_chunk: bytes):
        """Feed audio captured from meeting (WASAPI loopback)."""
        if not self._running or not self._inbound_stream:
            return
        is_speech, filtered = self._inbound_vad.process(audio_chunk)
        if is_speech:
            logger.debug(f"Inbound speech detected: {len(filtered)} bytes")
            await self._inbound_stream.send_audio(filtered)

    async def feed_mic_audio(self, audio_chunk: bytes):
        """Feed audio captured from user's microphone."""
        if not self._running or not self._outbound_stream:
            return
        is_speech, filtered = self._outbound_vad.process(audio_chunk)
        if is_speech:
            logger.debug(f"Outbound speech detected: {len(filtered)} bytes")
            await self._outbound_stream.send_audio(filtered)

    # ── Inbound callbacks (EN→ZH, for subtitles) ──

    async def _on_inbound_transcript(self, data: dict):
        """English transcript from meeting audio → translate to Chinese."""
        text = data.get("text", "")
        is_final = data.get("is_final", False)

        # Show English transcript
        await self.on_subtitle({
            "type": "transcript",
            "text": text,
            "is_final": is_final,
            "lang": "en",
        })

        # Translate to Chinese (only for final results to reduce API calls)
        if is_final and text.strip():
            translated = await self.translator.translate(text, "en", "zh")
            if translated:
                await self.on_subtitle({
                    "type": "translation",
                    "text": translated,
                    "is_final": True,
                    "lang": "zh",
                })

    # ── Outbound callbacks (ZH→EN, for TTS) ──

    async def _on_outbound_transcript(self, data: dict):
        """Chinese transcript of user's speech → translate to English → TTS."""
        text = data.get("text", "")
        is_final = data.get("is_final", False)

        # Show Chinese transcript
        await self.on_subtitle({
            "type": "user_transcript",
            "text": text,
            "is_final": is_final,
            "lang": "zh",
        })

        # Translate to English and queue for TTS (only for final results)
        if is_final and text.strip():
            translated = await self.translator.translate(text, "zh", "en")
            if translated:
                segments = self._segmenter.feed(translated, is_final=True)
                for seg in segments:
                    self._tts_queue.put_nowait(seg)

    # ── TTS consumer ──

    async def _tts_consumer(self):
        """Consume sentences from queue and generate TTS audio."""
        logger.info("TTS consumer started")
        try:
            while self._running:
                sentence = await self._tts_queue.get()
                if sentence is None:
                    break

                t0 = time.monotonic()
                try:
                    async for audio_chunk in self.elevenlabs.stream_tts(
                        sentence, self.voice_id
                    ):
                        await self.on_outbound_audio(audio_chunk)
                    latency = (time.monotonic() - t0) * 1000
                    logger.debug(f"TTS latency: {latency:.0f}ms for: {sentence[:30]}")
                except Exception as e:
                    logger.error(f"TTS error: {e}")
        except asyncio.CancelledError:
            pass
        logger.info("TTS consumer stopped")

    @property
    def is_running(self) -> bool:
        return self._running
