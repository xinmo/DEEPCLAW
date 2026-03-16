import logging

logger = logging.getLogger(__name__)


class Segmenter:
    """Intelligent sentence segmenter for real-time translation.

    Buffers translated text and emits complete sentences for TTS,
    balancing latency (shorter segments) vs translation quality (longer).
    """

    # Sentence-ending punctuation
    STRONG_BREAKS = {".", "!", "?", "。", "！", "？"}
    # Clause-level punctuation (emit if buffer gets long)
    WEAK_BREAKS = {",", ";", ":", "，", "；", "："}

    MAX_BUFFER_CHARS = 120  # Force emit if buffer exceeds this
    MIN_SEGMENT_CHARS = 8   # Don't emit too-short segments

    def __init__(self):
        self._buffer = ""

    def feed(self, text: str, is_final: bool = False) -> list[str]:
        """Feed translated text, return list of segments ready for TTS."""
        self._buffer += text
        segments = []

        if is_final and self._buffer.strip():
            segments.append(self._buffer.strip())
            self._buffer = ""
            return segments

        while True:
            seg = self._try_extract()
            if seg is None:
                break
            segments.append(seg)

        return segments

    def _try_extract(self) -> str | None:
        """Try to extract one segment from the buffer."""
        buf = self._buffer

        # Look for strong sentence breaks
        for i, ch in enumerate(buf):
            if ch in self.STRONG_BREAKS and i + 1 >= self.MIN_SEGMENT_CHARS:
                segment = buf[: i + 1].strip()
                self._buffer = buf[i + 1 :]
                return segment if segment else None

        # If buffer is long, look for weak breaks
        if len(buf) > self.MAX_BUFFER_CHARS:
            for i in range(len(buf) - 1, -1, -1):
                if buf[i] in self.WEAK_BREAKS:
                    segment = buf[: i + 1].strip()
                    self._buffer = buf[i + 1 :]
                    return segment if segment else None
            # No break found, force emit
            segment = buf.strip()
            self._buffer = ""
            return segment if segment else None

        return None

    def flush(self) -> str | None:
        """Flush remaining buffer content."""
        if self._buffer.strip():
            seg = self._buffer.strip()
            self._buffer = ""
            return seg
        return None

    def reset(self):
        self._buffer = ""
