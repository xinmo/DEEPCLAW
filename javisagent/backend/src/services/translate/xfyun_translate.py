"""科大讯飞 (iFlytek) Machine Translation Service.

Uses iFlytek's machine translation API for text translation
between Chinese and English.
"""

import logging
import hmac
import hashlib
import base64
from typing import Optional
from datetime import datetime
from urllib.parse import urlencode, urlparse

import httpx

from .config import get_translate_settings

logger = logging.getLogger(__name__)
settings = get_translate_settings()

# 讯飞机器翻译 API 地址
XFYUN_TRANS_URL = "https://itrans.xfyun.cn/v2/its"


class XfyunTranslateService:
    """iFlytek Machine Translation service."""

    def __init__(self):
        self.app_id = settings.xfyun_app_id
        self.api_key = settings.xfyun_api_key
        self.api_secret = settings.xfyun_api_secret
        self._client = httpx.AsyncClient(timeout=10.0)

    def _generate_auth_url(self) -> str:
        """Generate authenticated URL with signature."""
        url = urlparse(XFYUN_TRANS_URL)
        date = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

        signature_origin = f"host: {url.netloc}\ndate: {date}\nPOST {url.path} HTTP/1.1"
        signature_sha = hmac.new(
            self.api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        signature = base64.b64encode(signature_sha).decode("utf-8")

        authorization_origin = (
            f'api_key="{self.api_key}", algorithm="hmac-sha256", '
            f'headers="host date request-line", signature="{signature}"'
        )
        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")

        params = {
            "authorization": authorization,
            "date": date,
            "host": url.netloc,
        }
        return f"{XFYUN_TRANS_URL}?{urlencode(params)}"

    async def translate(
        self,
        text: str,
        source_lang: str = "zh",
        target_lang: str = "en",
    ) -> Optional[str]:
        """Translate text using iFlytek Machine Translation."""
        if not text.strip():
            return ""

        # Language mapping for iFlytek
        lang_map = {"zh": "cn", "en": "en"}
        src = lang_map.get(source_lang, "cn")
        tgt = lang_map.get(target_lang, "en")

        # Build request body
        body = {
            "common": {"app_id": self.app_id},
            "business": {"from": src, "to": tgt},
            "data": {
                "text": base64.b64encode(text.encode("utf-8")).decode("utf-8"),
            },
        }

        try:
            url = self._generate_auth_url()
            response = await self._client.post(
                url,
                json=body,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            result = response.json()
            code = result.get("code")

            if code == 0:
                trans_result = result.get("data", {}).get("result", {})
                trans_text = trans_result.get("trans_result", {}).get("dst", "")
                return trans_text
            else:
                logger.error(f"iFlytek translate error: code={code}, msg={result.get('message')}")
                return None

        except Exception as e:
            logger.error(f"iFlytek translate request failed: {e}")
            return None

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
