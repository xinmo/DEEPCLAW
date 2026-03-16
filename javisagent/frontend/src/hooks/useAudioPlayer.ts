import { useRef, useCallback } from "react";

export function useAudioPlayer() {
  const ctxRef = useRef<AudioContext | null>(null);
  const nextTimeRef = useRef(0);

  const getContext = useCallback(() => {
    if (!ctxRef.current) {
      ctxRef.current = new AudioContext({ sampleRate: 16000 });
    }
    return ctxRef.current;
  }, []);

  const playChunk = useCallback(
    (base64Audio: string) => {
      const ctx = getContext();
      const binary = atob(base64Audio);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
      }

      // Convert 16-bit PCM to Float32
      const int16 = new Int16Array(bytes.buffer);
      const float32 = new Float32Array(int16.length);
      for (let i = 0; i < int16.length; i++) {
        float32[i] = int16[i] / 32768;
      }

      const buffer = ctx.createBuffer(1, float32.length, 16000);
      buffer.getChannelData(0).set(float32);

      const source = ctx.createBufferSource();
      source.buffer = buffer;
      source.connect(ctx.destination);

      const now = ctx.currentTime;
      const startTime = Math.max(now, nextTimeRef.current);
      source.start(startTime);
      nextTimeRef.current = startTime + buffer.duration;
    },
    [getContext]
  );

  const stop = useCallback(() => {
    ctxRef.current?.close();
    ctxRef.current = null;
    nextTimeRef.current = 0;
  }, []);

  return { playChunk, stop };
}
