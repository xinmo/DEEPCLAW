"""科大讯飞 (iFlytek) Real-time ASR Service.

Uses iFlytek's real-time speech transcription API (实时语音转写)
for streaming speech recognition with Chinese and English support.
"""

import json
import asyncio
import logging
import time
import hmac
import hashlib
import base64
from typing import Callable, Optional
from urllib.parse import urlencode

import websockets

from .config import get_translate_settings

logger = logging.getLogger(__name__)
settings = get_translate_settings()

# 讯飞实时语音转写 WebSocket 地址
XFYUN_ASR_WS_URL = "wss://rtasr.xfyun.cn/v1/ws"


class XfyunASRService:
    """iFlytek Real-time ASR service for streaming speech recognition."""

    def __init__(self):
        self.app_id = settings.xfyun_app_id
        self.api_key = settings.xfyun_api_key

    async def create_stream(
        self,
        source_lang: str = "zh",
        on_transcript: Optional[Callable] = None,
    ) -> "XfyunASRStream":
        """Create a new streaming ASR session."""
        stream = XfyunASRStream(
            app_id=self.app_id,
            api_key=self.api_key,
            source_lang=source_lang,
            on_transcript=on_transcript,
        )
        await stream.connect()
        return stream


class XfyunASRStream:
    """A single iFlytek ASR streaming session."""

    def __init__(
        self,
        app_id: str,
        api_key: str,
        source_lang: str = "zh",
        on_transcript: Optional[Callable] = None,
    ):
        self.app_id = app_id
        self.api_key = api_key
        self.source_lang = source_lang
        self.on_transcript = on_transcript
        self._ws = None
        self._receive_task: Optional[asyncio.Task] = None
        self._running = False

    def _generate_signature(self) -> tuple[str, str]:
        """Generate signature for iFlytek API authentication."""
        ts = str(int(time.time()))
        base_string = self.app_id + ts
        signature = hmac.new(
            self.api_key.encode("utf-8"),
            base_string.encode("utf-8"),
            hashlib.md5,
        ).hexdigest()
        return ts, base64.b64encode(signature.encode("utf-8")).decode("utf-8")

    async def connect(self):
        """Connect to iFlytek ASR WebSocket."""
        ts, signa = self._generate_signature()

        # Language mapping: zh=中文, en=英文
        lang_map = {"zh": "cn", "en": "en"}
        lang = lang_map.get(self.source_lang, "cn")

        params = {
            "appid": self.app_id,
            "ts": ts,
            "signa": signa,
            "lang": lang,
            "punc": "1",  # Enable punctuation
        }

        url = f"{XFYUN_ASR_WS_URL}?{urlencode(params)}"
        self._ws = await websockets.connect(url)
        self._running = True
        self._receive_task = asyncio.create_task(self._receive_loop())
        logger.info(f"iFlytek ASR stream connected: {self.source_lang}")

    async def send_audio(self, audio_chunk: bytes):
        """Send PCM audio chunk to iFlytek for recognition."""
        if self._ws and self._running:
            # iFlytek expects base64 encoded audio
            encoded = base64.b64encode(audio_chunk).decode("utf-8")
            await self._ws.send(encoded)

    async def _receive_loop(self):
        """Receive transcription results from iFlytek."""
        try:
            async for message in self._ws:
                if not self._running:
                    break
                if isinstance(message, str):
                    data = json.loads(message)
                    code = data.get("code")

                    if code == "0":
                        # Success
                        result_data = data.get("data", {})
                        result = result_data.get("result", {})
                        ws_list = result.get("ws", [])

                        # Extract text from word segments
                        text = ""
                        for ws in ws_list:
                            cw_list = ws.get("cw", [])
                            for cw in cw_list:
                                text += cw.get("w", "")

                        if text and self.on_transcript:
                            # type: 0=final, 1=intermediate
                            is_final = result_data.get("type") == "0"
                            await self.on_transcript({
                                "text": text,
                                "is_final": is_final,
                            })

                    elif code != "0":
                        logger.error(f"iFlytek ASR error: code={code}, msg={data.get('message')}")

        except websockets.ConnectionClosed as e:
            logger.warning(f"iFlytek ASR connection closed: {e}")
        except Exception as e:
            logger.error(f"iFlytek ASR receive error: {e}")
        finally:
            self._running = False

    async def close(self):
        """Close the ASR session."""
        self._running = False

        if self._ws:
            # Send end signal
            try:
                await self._ws.send('{"end": true}')
            except Exception:
                pass

        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass

        logger.info("iFlytek ASR stream closed")

    @property
    def is_running(self) -> bool:
        return self._running
