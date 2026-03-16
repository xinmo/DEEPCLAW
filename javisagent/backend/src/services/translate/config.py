from pydantic_settings import BaseSettings
from functools import lru_cache


class TranslateSettings(BaseSettings):
    elevenlabs_api_key: str = ""
    deepl_api_key: str = ""

    # ElevenLabs
    elevenlabs_base_url: str = "https://api.elevenlabs.io/v1"
    elevenlabs_ws_url: str = "wss://api.elevenlabs.io/v1"
    elevenlabs_tts_model: str = "eleven_flash_v2_5"

    # 科大讯飞 (iFlytek)
    xfyun_app_id: str = ""
    xfyun_api_key: str = ""
    xfyun_api_secret: str = ""

    # Audio
    sample_rate: int = 16000
    channels: int = 1
    chunk_duration_ms: int = 100

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "allow"}


@lru_cache
def get_translate_settings() -> TranslateSettings:
    return TranslateSettings()
