import logging

logger = logging.getLogger(__name__)


class VAD:
    """Voice Activity Detection using webrtcvad.

    Filters out silence/noise from audio streams before sending to ASR,
    reducing API costs and improving recognition quality.
    """

    def __init__(self, aggressiveness: int = 2, sample_rate: int = 16000):
        """
        Args:
            aggressiveness: 0-3, higher = more aggressive filtering
            sample_rate: must be 8000, 16000, 32000, or 48000
        """
        import webrtcvad

        self.vad = webrtcvad.Vad(aggressiveness)
        self.sample_rate = sample_rate
        # webrtcvad requires frames of 10, 20, or 30 ms
        self.frame_duration_ms = 30
        self.frame_size = int(sample_rate * self.frame_duration_ms / 1000) * 2  # 16-bit

        self._speech_frames = 0
        self._silence_frames = 0
        self._is_speaking = False

        # Thresholds for state transitions
        self.speech_threshold = 3   # consecutive speech frames to start
        self.silence_threshold = 15  # consecutive silence frames to stop

    def process(self, audio_chunk: bytes) -> tuple[bool, bytes]:
        """Process audio chunk, return (is_speech, filtered_audio).

        Returns the audio only if speech is detected.
        """
        speech_audio = bytearray()
        is_speech = False

        # Process in webrtcvad-compatible frames
        offset = 0
        while offset + self.frame_size <= len(audio_chunk):
            frame = audio_chunk[offset : offset + self.frame_size]
            offset += self.frame_size

            try:
                frame_is_speech = self.vad.is_speech(frame, self.sample_rate)
            except Exception:
                frame_is_speech = True  # Pass through on error

            if frame_is_speech:
                self._speech_frames += 1
                self._silence_frames = 0
                if self._speech_frames >= self.speech_threshold:
                    self._is_speaking = True
            else:
                self._silence_frames += 1
                self._speech_frames = 0
                if self._silence_frames >= self.silence_threshold:
                    self._is_speaking = False

            if self._is_speaking:
                speech_audio.extend(frame)
                is_speech = True

        return is_speech, bytes(speech_audio)

    def reset(self):
        self._speech_frames = 0
        self._silence_frames = 0
        self._is_speaking = False

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking
