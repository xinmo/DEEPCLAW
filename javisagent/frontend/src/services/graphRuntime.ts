/**
 * graphRuntime.ts
 * Lazy-loads @antv/g6 and provides localStorage helpers for KnowledgeGraph state persistence.
 */

export type GraphViewMode = "summary" | "explorer" | "interactive";

// -- Lazy G6 runtime loader --

let g6Promise: Promise<typeof import("@antv/g6")> | null = null;

export function loadGraphRuntime(): Promise<typeof import("@antv/g6")> {
  if (!g6Promise) {
    g6Promise = import("@antv/g6");
  }
  return g6Promise;
}

export function prefetchGraphRuntime(): void {
  loadGraphRuntime();
}

let prefetchScheduled = false;
export function scheduleGraphRuntimePrefetch(): void {
  if (prefetchScheduled) return;
  prefetchScheduled = true;
  setTimeout(() => {
    loadGraphRuntime();
  }, 2000);
}

// -- localStorage state helpers --

function storageKey(baseKey: string | undefined, suffix: string): string {
  return `kg_graph_${baseKey ?? "default"}_${suffix}`;
}

export function readStoredGraphViewMode(
  baseKey: string | undefined,
  defaultMode: GraphViewMode
): GraphViewMode {
  try {
    const raw = localStorage.getItem(storageKey(baseKey, "viewMode"));
    if (raw === "summary" || raw === "explorer" || raw === "interactive") {
      return raw;
    }
  } catch {
    // ignore
  }
  return defaultMode;
}

export function writeStoredGraphViewMode(
  baseKey: string | undefined,
  mode: GraphViewMode
): void {
  try {
    localStorage.setItem(storageKey(baseKey, "viewMode"), mode);
  } catch {
    // ignore
  }
}

export function readStoredGraphState<T>(
  baseKey: string | undefined,
  suffix: string,
  defaultValue: T,
  parse: (raw: unknown) => T | undefined | null
): T {
  try {
    const raw = localStorage.getItem(storageKey(baseKey, suffix));
    if (raw != null) {
      const parsed = parse(JSON.parse(raw));
      if (parsed != null) return parsed;
    }
  } catch {
    // ignore
  }
  return defaultValue;
}

export function writeStoredGraphState(
  baseKey: string | undefined,
  suffix: string,
  value: unknown
): void {
  try {
    localStorage.setItem(storageKey(baseKey, suffix), JSON.stringify(value));
  } catch {
    // ignore
  }
}
