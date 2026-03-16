# Claw Global Middleware Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add global user-level `MemoryMiddleware`, `SkillsMiddleware`, `SummarizationToolMiddleware`, and CLI `LocalContextMiddleware` to Claw, while extending prompt management and conversation prompt snapshots for the new editable prompt surfaces.

**Architecture:** Reuse the existing deepagents and CLI middleware implementations, but wire them through Claw-controlled user-home storage routes and the existing prompt registry. Keep `LocalContextMiddleware` as a fixed internal capability, while snapshotting the newly editable prompt overrides per conversation.

**Tech Stack:** FastAPI, SQLAlchemy, React, local deepagents SDK, local deepagents CLI middleware, TypeScript, pytest.

---

### Task 1: Extend deepagents prompt override surfaces

**Files:**
- Modify: `javisagent/libs/deepagents/deepagents/middleware/memory.py`
- Modify: `javisagent/libs/deepagents/deepagents/middleware/skills.py`
- Modify: `javisagent/libs/deepagents/deepagents/middleware/summarization.py`
- Modify: `javisagent/libs/deepagents/deepagents/graph.py`

**Steps:**
1. Add injectable prompt-template support to `MemoryMiddleware`.
2. Add injectable prompt-template support to `SkillsMiddleware`.
3. Add injectable system-prompt support to `SummarizationToolMiddleware` and its factory.
4. Extend `create_deep_agent()` override handling to accept the new prompt keys.

### Task 2: Add Claw user-home global storage wiring

**Files:**
- Modify: `javisagent/backend/src/services/claw/agent.py`

**Steps:**
1. Define user-home paths for `~/.memory/AGENTS.md`, `~/.agent/skills`, and `~/.conversation_history`.
2. Ensure those directories and the memory file exist at agent-creation time.
3. Replace the current ephemeral-only composite backend routing with stable user-home routes plus the existing working-directory shell backend.
4. Add CLI `LocalContextMiddleware` to the Claw middleware stack.
5. Add `MemoryMiddleware`, `SkillsMiddleware`, and `SummarizationToolMiddleware` to the Claw middleware stack.

### Task 3: Expand prompt registry and snapshot coverage

**Files:**
- Modify: `javisagent/backend/src/services/claw/prompt_registry.py`
- Modify: `javisagent/backend/src/routes/claw/conversations.py`
- Modify: `javisagent/backend/src/routes/claw/chat.py`

**Steps:**
1. Register `memory_system_prompt`, `skills_system_prompt`, and `summarization_tool_system_prompt`.
2. Include the new keys in the prompt bundle normalization and override builder.
3. Keep `LocalContextMiddleware` out of the registry and prompt snapshots.
4. Ensure new conversations snapshot the expanded bundle.
5. Ensure older conversations backfill missing keys on first chat after upgrade.

### Task 4: Verify behavior with focused tests

**Files:**
- Modify or create: `javisagent/backend/tests/test_claw_prompt_snapshots.py`
- Create if needed: `javisagent/backend/tests/test_claw_agent_middleware.py`

**Steps:**
1. Test that conversation creation snapshots the new prompt keys.
2. Test that legacy conversations backfill missing prompt keys.
3. Test that Claw agent creation wires global user-home routes and includes the new middleware.
4. Run Python syntax checks and targeted pytest.
5. Run frontend TypeScript build to confirm prompt page compatibility.
