export const CLAW_STREAM_STATUS_EVENT = "javis:claw-stream-status";

export interface ClawStreamStatusDetail {
  sending: boolean;
  conversationId: string | null;
  conversationTitle: string | null;
}

export function dispatchClawStreamStatus(detail: ClawStreamStatusDetail) {
  window.dispatchEvent(
    new CustomEvent<ClawStreamStatusDetail>(CLAW_STREAM_STATUS_EVENT, {
      detail,
    }),
  );
}
