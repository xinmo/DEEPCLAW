# Claw Chat CLI-Parity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rebuild Claw chat streaming so the web UI shows tool calls, shell execution, planning, and subagent activity with CLI-level visibility and correct ordering.

**Architecture:** Move Claw chat from a message-with-attachments model to a stream-driven timeline model. The backend will emit richer SSE events derived from the same `messages + updates + subgraphs` stream that powers the CLI, persist normalized process records, and return hydrated history. The frontend will consume those events into a typed timeline reducer and render specialized cards for text, shell, tool, planning, and subagent items.

**Tech Stack:** FastAPI, SQLAlchemy, LangGraph/Deep Agents stream API, React 19, TypeScript, Ant Design, Playwright, pytest

---

## Recommended Approach

### Option A: Styling-only patch

Keep the current SSE contract and improve `ToolCallCard`, `SubAgentCard`, and `PlanningCard` only.

**Why not:** This does not solve missing event types, ordering loss, shell output truncation, or history replay gaps.

### Option B: Frontend-only reducer rewrite

Keep the current backend mostly unchanged and make the frontend infer timeline structure from `text/tool_call/tool_result`.

**Why not:** The backend still does not emit planning or subagent process events, and shell output remains an opaque string blob.

### Option C: Protocol-first CLI parity

Align the backend stream contract with the CLI event model, then build a dedicated timeline renderer on the frontend.

**Recommendation:** Choose this approach. It is the only option that fixes correctness, feature coverage, and replayability together.

---

### Task 1: Define the stream contract and history model

**Files:**
- Modify: `javisagent/backend/src/routes/claw/chat.py`
- Modify: `javisagent/backend/src/schemas/claw.py`
- Modify: `javisagent/frontend/src/types/claw.ts`
- Create: `javisagent/backend/tests/test_claw_chat_stream.py`

**Step 1: Write the failing backend stream contract test**

Create `javisagent/backend/tests/test_claw_chat_stream.py` with tests that assert the chat stream can emit:
- `text`
- `tool_call_started`
- `tool_call_delta`
- `tool_call_completed`
- `shell_started`
- `shell_output`
- `shell_completed`
- `planning_started`
- `planning_updated`
- `subagent_started`
- `subagent_updated`
- `subagent_completed`
- `done`

Use a fake stream generator or patched `agent.astream(...)` to return deterministic `messages`, `updates`, and subgraph chunks.

**Step 2: Run the new test to verify it fails**

Run:

```bash
cd javisagent/backend
python -m pytest tests/test_claw_chat_stream.py -q
```

Expected: FAIL because the current route only emits `text/tool_call/tool_result/done/error`.

**Step 3: Define normalized event types**

Update `javisagent/frontend/src/types/claw.ts` so `SSEEvent` becomes a discriminated union instead of `[key: string]: any`.

Add explicit payload types for:
- timeline text chunks
- tool lifecycle events
- shell lifecycle events
- planning lifecycle events
- subagent lifecycle events
- stream completion and errors

Also update backend schema objects so history responses can return structured process items instead of only `content + tool_calls`.

**Step 4: Implement the minimal backend/frontend type alignment**

In `javisagent/backend/src/routes/claw/chat.py`, introduce one serializer function per emitted event type.

In `javisagent/backend/src/schemas/claw.py`, add schema classes such as:

```python
class ProcessEventResponse(BaseModel):
    id: str
    kind: str
    title: str
    status: str
    data: dict = {}
    created_at: datetime
```

In `javisagent/frontend/src/types/claw.ts`, add:

```ts
export type TimelineItem =
  | TextTimelineItem
  | ToolTimelineItem
  | ShellTimelineItem
  | PlanningTimelineItem
  | SubAgentTimelineItem;
```

**Step 5: Run tests and type-checking**

Run:

```bash
cd javisagent/backend
python -m pytest tests/test_claw_chat_stream.py -q
cd ../frontend
npx tsc --noEmit --jsx react-jsx --moduleResolution bundler --module esnext --target es2020 --lib dom,es2020 --skipLibCheck src/types/claw.ts
```

Expected: backend test still partially failing until later tasks, but types compile cleanly.

**Step 6: Commit**

```bash
git add javisagent/backend/src/routes/claw/chat.py javisagent/backend/src/schemas/claw.py javisagent/frontend/src/types/claw.ts javisagent/backend/tests/test_claw_chat_stream.py
git commit -m "test: define Claw streaming contract and timeline types"
```

---

### Task 2: Emit CLI-equivalent backend events from `messages + updates + subgraphs`

**Files:**
- Modify: `javisagent/backend/src/routes/claw/chat.py`
- Reference: `javisagent/libs/cli/deepagents_cli/textual_adapter.py`
- Reference: `javisagent/libs/cli/deepagents_cli/widgets/messages.py`
- Test: `javisagent/backend/tests/test_claw_chat_stream.py`

**Step 1: Write failing cases for updates and subgraph handling**

Extend `test_claw_chat_stream.py` with cases that simulate:
- `tool_call_chunk/tool_call`
- `ToolMessage`
- `updates` payloads for planning/todos
- subgraph namespace events from task/subagent execution

Assert the route emits stable IDs and ordered lifecycle events.

**Step 2: Run test to verify it fails**

Run:

```bash
cd javisagent/backend
python -m pytest tests/test_claw_chat_stream.py -q
```

Expected: FAIL on missing `updates/subgraphs` coverage.

**Step 3: Switch backend streaming to the CLI-style source**

Update `agent.astream(...)` in `javisagent/backend/src/routes/claw/chat.py` to use:

```python
async for chunk in agent.astream(
    input_data,
    stream_mode=["messages", "updates"],
    subgraphs=True,
):
```

Then process:
- main-agent text from `messages`
- tool call chunks from `message.content_blocks`
- planning/todo updates from `updates`
- subagent state from namespaced chunks

**Step 4: Add event serializers**

Implement helpers such as:

```python
def sse_event(event_type: str, **payload) -> str: ...
def emit_tool_started(...): ...
def emit_shell_output(...): ...
def emit_subagent_updated(...): ...
```

Special handling:
- map `shell/bash/execute` to dedicated shell events
- preserve tool IDs from chunk buffers
- emit shell output deltas without truncating to 500 chars
- only emit main-agent text to chat bubbles

**Step 5: Run tests**

Run:

```bash
cd javisagent/backend
python -m pytest tests/test_claw_chat_stream.py -q
python -m py_compile src/routes/claw/chat.py
```

Expected: PASS.

**Step 6: Commit**

```bash
git add javisagent/backend/src/routes/claw/chat.py javisagent/backend/tests/test_claw_chat_stream.py
git commit -m "feat: emit Claw process events with CLI-style streaming"
```

---

### Task 3: Persist process items so refresh and history replay work

**Files:**
- Modify: `javisagent/backend/src/models/claw.py`
- Modify: `javisagent/backend/src/routes/claw/chat.py`
- Modify: `javisagent/backend/src/routes/claw/conversations.py`
- Modify: `javisagent/backend/src/schemas/claw.py`
- Create: `javisagent/backend/tests/test_claw_chat_history.py`

**Step 1: Write the failing history replay test**

Create `javisagent/backend/tests/test_claw_chat_history.py` that:
- sends a chat containing text + tool + shell + planning + subagent activity
- requests `GET /api/claw/conversations/{id}/messages`
- asserts the returned history includes normalized process items in order

**Step 2: Run test to verify it fails**

Run:

```bash
cd javisagent/backend
python -m pytest tests/test_claw_chat_history.py -q
```

Expected: FAIL because only `ClawMessage.content` and relation-backed `tool_calls` are returned today.

**Step 3: Persist process records**

Recommended minimal model addition:

```python
class ClawProcessEvent(Base):
    __tablename__ = "claw_process_events"
    id = Column(String, primary_key=True)
    message_id = Column(String, ForeignKey("claw_messages.id", ondelete="CASCADE"))
    kind = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    data = Column(JSON, default={})
    sequence = Column(Integer, nullable=False)
```

Persist every tool/shell/planning/subagent event with stable IDs and sequence numbers. Keep `ClawToolCall` only if you still want a tool-specific relation; otherwise replace it with `ClawProcessEvent`.

**Step 4: Hydrate history responses**

Update `get_messages(...)` so assistant messages return:
- final text content
- normalized `process_events`
- any final metadata needed for replay

Do not force the frontend to reconstruct history from `extra_data`.

**Step 5: Run tests**

Run:

```bash
cd javisagent/backend
python -m pytest tests/test_claw_chat_history.py tests/test_claw_chat_stream.py -q
```

Expected: PASS.

**Step 6: Commit**

```bash
git add javisagent/backend/src/models/claw.py javisagent/backend/src/routes/claw/chat.py javisagent/backend/src/routes/claw/conversations.py javisagent/backend/src/schemas/claw.py javisagent/backend/tests/test_claw_chat_history.py
git commit -m "feat: persist and replay Claw process timeline"
```

---

### Task 4: Replace the frontend message-attached state with a timeline reducer

**Files:**
- Modify: `javisagent/frontend/src/pages/ClawChatPage.tsx`
- Modify: `javisagent/frontend/src/types/claw.ts`
- Modify: `javisagent/frontend/src/services/clawApi.ts`
- Create: `javisagent/frontend/src/components/Claw/TimelineItemRenderer.tsx`
- Create: `javisagent/frontend/tests/e2e/claw-chat-stream.spec.ts`

**Step 1: Write the failing Playwright scenario**

Create `javisagent/frontend/tests/e2e/claw-chat-stream.spec.ts`.

Mock:
- `GET /api/claw/conversations`
- `POST /api/claw/conversations`
- `GET /api/claw/conversations/:id/messages`
- `POST /api/claw/conversations/:id/chat`

Return an SSE body containing:
- intro text
- `tool_call_started`
- `shell_started`
- `shell_output`
- `shell_completed`
- final text
- `done`

Assert the page renders all items in order.

**Step 2: Run test to verify it fails**

Run:

```bash
cd javisagent/frontend
npx playwright test tests/e2e/claw-chat-stream.spec.ts --project=chromium
```

Expected: FAIL because the current page stores process items under assistant bubbles instead of as ordered timeline nodes.

**Step 3: Add a reducer-driven timeline store**

Inside `ClawChatPage.tsx`, replace the current `messages: ChatMessage[]` update strategy with:

```ts
type ChatState = {
  timeline: TimelineItem[];
  currentAssistantId: string | null;
};

function reduceStreamEvent(state: ChatState, event: SSEEvent): ChatState { ... }
```

Requirements:
- never mutate external variables inside `setState`
- preserve strict event ordering
- treat text/process items as first-class timeline nodes
- support history hydration with the same shape used by the live stream

**Step 4: Render a real timeline**

Replace bubble-plus-nested-cards rendering with:
- user bubble items
- assistant text items
- tool items
- shell items
- planning items
- subagent items

Create `TimelineItemRenderer.tsx` to dispatch by `item.kind`.

**Step 5: Run tests**

Run:

```bash
cd javisagent/frontend
npx tsc --noEmit --jsx react-jsx --moduleResolution bundler --module esnext --target es2020 --lib dom,es2020 --skipLibCheck src/pages/ClawChatPage.tsx src/components/Claw/TimelineItemRenderer.tsx
npx playwright test tests/e2e/claw-chat-stream.spec.ts --project=chromium
```

Expected: PASS.

**Step 6: Commit**

```bash
git add javisagent/frontend/src/pages/ClawChatPage.tsx javisagent/frontend/src/types/claw.ts javisagent/frontend/src/services/clawApi.ts javisagent/frontend/src/components/Claw/TimelineItemRenderer.tsx javisagent/frontend/tests/e2e/claw-chat-stream.spec.ts
git commit -m "feat: render Claw chat as ordered process timeline"
```

---

### Task 5: Add CLI-style specialized renderers for tool, shell, planning, and task/subagent output

**Files:**
- Modify: `javisagent/frontend/src/components/Claw/ToolCallCard.tsx`
- Modify: `javisagent/frontend/src/components/Claw/SubAgentCard.tsx`
- Modify: `javisagent/frontend/src/components/Claw/PlanningCard.tsx`
- Create: `javisagent/frontend/src/components/Claw/ShellCallCard.tsx`
- Create: `javisagent/frontend/src/components/Claw/TextTimelineCard.tsx`
- Create: `javisagent/frontend/src/components/Claw/ProcessGroupCard.tsx`
- Test: `javisagent/frontend/tests/e2e/claw-chat-stream.spec.ts`

**Step 1: Extend the failing Playwright test**

Add assertions for:
- shell command header display (`$ command`)
- stdout/stderr block formatting
- expanded error state on failed shell/tool calls
- web search result formatting with title + URL, not raw escaped JSON
- subagent/task result rendering

**Step 2: Run test to verify it fails**

Run:

```bash
cd javisagent/frontend
npx playwright test tests/e2e/claw-chat-stream.spec.ts --project=chromium
```

Expected: FAIL because `ToolCallCard` currently falls back to `JSON.stringify(...)` for most outputs.

**Step 3: Mirror CLI formatter behavior**

Use `javisagent/libs/cli/deepagents_cli/widgets/messages.py` as the reference for formatter logic.

Implement frontend render rules:
- `shell/bash/execute`: show command header, streaming output body, exit status, error badge
- `web_search/fetch_url/http_request`: show title + URL + summary list
- filesystem tools: show file names / file body / grep hits
- `task`: show task title, status, result preview
- planning/todos: show ordered checklist with statuses

Do not render escaped JSON unless the tool is unknown.

**Step 4: Improve visual hierarchy**

Keep a compact process style:
- no full assistant avatar per process row
- lighter chrome than text bubbles
- status-first headers
- optional expand/collapse for verbose output
- grouped shell output with monospace block

**Step 5: Run tests**

Run:

```bash
cd javisagent/frontend
npx tsc --noEmit --jsx react-jsx --moduleResolution bundler --module esnext --target es2020 --lib dom,es2020 --skipLibCheck src/components/Claw/*.tsx
npx playwright test tests/e2e/claw-chat-stream.spec.ts --project=chromium
```

Expected: PASS.

**Step 6: Commit**

```bash
git add javisagent/frontend/src/components/Claw/ToolCallCard.tsx javisagent/frontend/src/components/Claw/SubAgentCard.tsx javisagent/frontend/src/components/Claw/PlanningCard.tsx javisagent/frontend/src/components/Claw/ShellCallCard.tsx javisagent/frontend/src/components/Claw/TextTimelineCard.tsx javisagent/frontend/src/components/Claw/ProcessGroupCard.tsx javisagent/frontend/tests/e2e/claw-chat-stream.spec.ts
git commit -m "feat: add CLI-style renderers for Claw process output"
```

---

### Task 6: Load stored history into the same timeline and verify full flows end-to-end

**Files:**
- Modify: `javisagent/frontend/src/pages/ClawChatPage.tsx`
- Modify: `javisagent/frontend/src/services/clawApi.ts`
- Modify: `javisagent/backend/src/routes/claw/chat.py`
- Modify: `javisagent/backend/src/routes/claw/conversations.py`
- Test: `javisagent/frontend/tests/e2e/claw-chat-history.spec.ts`
- Test: `javisagent/backend/tests/test_claw_chat_history.py`

**Step 1: Write the failing history hydration test**

Create `javisagent/frontend/tests/e2e/claw-chat-history.spec.ts`.

Mock `GET /api/claw/conversations/:id/messages` to return:
- user message
- assistant text timeline items
- stored tool/shell/planning/subagent items

Assert the page renders the same structure without opening a live stream.

**Step 2: Run test to verify it fails**

Run:

```bash
cd javisagent/frontend
npx playwright test tests/e2e/claw-chat-history.spec.ts --project=chromium
```

Expected: FAIL because current history loading only maps `id/role/content`.

**Step 3: Hydrate timeline from history**

Update `clawApi.getMessages(...)` and `ClawChatPage.tsx` so the page loads historical timeline items into the exact same state shape used for live events.

Avoid separate render paths for:
- live stream
- reloaded history

They must share one reducer and one renderer.

**Step 4: Run end-to-end checks**

Run:

```bash
cd javisagent/backend
python -m pytest tests/test_claw_chat_stream.py tests/test_claw_chat_history.py -q
cd ../frontend
npx playwright test tests/e2e/claw-chat-stream.spec.ts tests/e2e/claw-chat-history.spec.ts --project=chromium
npx tsc --noEmit
```

Expected: PASS.

**Step 5: Manual verification**

Run the app and verify:
1. Ask a tool-free question: only user + assistant text appear.
2. Ask a web search question: intro text, search card, final summary appear in order.
3. Ask a shell-heavy task: command, output stream, completion, and final assistant summary all appear.
4. Refresh the page: the same process timeline reappears from history.

**Step 6: Commit**

```bash
git add javisagent/frontend/src/pages/ClawChatPage.tsx javisagent/frontend/src/services/clawApi.ts javisagent/backend/src/routes/claw/chat.py javisagent/backend/src/routes/claw/conversations.py javisagent/frontend/tests/e2e/claw-chat-history.spec.ts javisagent/backend/tests/test_claw_chat_history.py
git commit -m "feat: hydrate and verify Claw timeline history"
```

---

## Notes for Implementation

- Do not keep process data nested under assistant message cards if you want CLI parity. Use an ordered timeline.
- Do not mutate outer variables inside React state updaters. This breaks under `StrictMode`.
- Do not stringify tool output too early on the backend. Preserve structured JSON for tool-specific renderers.
- Do not truncate shell output in the SSE protocol. Truncation belongs in the UI preview layer.
- Do not rely on `message.content` alone. Prefer `content_blocks` and chunk-level metadata.
- Keep the backend history format isomorphic with the live stream format.

## Suggested Commit Order

1. Stream contract and types
2. Backend event emission
3. Backend persistence and history
4. Frontend reducer and timeline
5. Specialized renderers
6. History hydration and end-to-end verification

