# Claw Chat 图片上传 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 让用户在 Claw Chat 对话框中上传图片（含粘贴截图），智能体通过视觉模型识别图片内容进行回答。

**Architecture:** 将 `MessageCreate.content` 从纯字符串扩展为 `str | list` 联合类型，复用 LangChain 原生多模态消息格式（OpenAI Vision / Anthropic Vision 统一格式）。图片仅以 base64 形式在请求中传输，不落盘不入库；DB 仅存文本部分，通过 `extra_data.has_images` 标记历史消息含图片。

**Tech Stack:** Python FastAPI + Pydantic v2, LangChain HumanMessage multimodal content, React + TypeScript + Ant Design, FileReader API (base64)

---

## Task 1: 后端 Schema 扩展

**Files:**
- Modify: `javisagent/backend/src/schemas/claw.py`

**Step 1: 阅读当前 Schema**

阅读 `javisagent/backend/src/schemas/claw.py` 第 28-45 行，确认 `MessageCreate` 当前结构。

**Step 2: 修改 `MessageCreate.content` 类型**

将：
```python
class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1)
    selected_skill: str | None = None
```

改为：
```python
class MessageCreate(BaseModel):
    content: str | list = Field(...)
    selected_skill: str | None = None

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str | list) -> str | list:
        if isinstance(v, str) and not v.strip():
            raise ValueError("content must not be empty")
        if isinstance(v, list) and len(v) == 0:
            raise ValueError("content list must not be empty")
        return v
```

需要在文件顶部确保导入 `from pydantic import BaseModel, Field, field_validator`。

**Step 3: 验证后端能启动**

```bash
cd javisagent/backend && python -c "from src.schemas.claw import MessageCreate; print('OK')"
```
Expected: `OK`

**Step 4: Commit**

```bash
git add javisagent/backend/src/schemas/claw.py
git commit -m "feat(claw): extend MessageCreate.content to support multimodal list"
```

---

## Task 2: 后端 chat.py 文本提取与 Agent 透传

**Files:**
- Modify: `javisagent/backend/src/routes/claw/chat.py`

**Step 1: 新增文本提取辅助函数**

在 `chat.py` 顶部函数区（`_normalize_tool_name` 附近）新增：

```python
def _extract_text_content(content: str | list) -> str:
    """从多模态 content 中提取纯文本，用于存入数据库。"""
    if isinstance(content, str):
        return content
    parts = [
        block["text"]
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    return " ".join(parts) or "[图片]"


def _count_images(content: str | list) -> int:
    """统计 content 中的图片数量。"""
    if isinstance(content, str):
        return 0
    return sum(
        1 for block in content
        if isinstance(block, dict) and block.get("type") == "image_url"
    )
```

**Step 2: 找到用户消息保存到 DB 的代码位置**

在 `chat_event_generator` 中搜索创建 `ClawMessage` 并设置 `role=MessageRole.USER` 的代码段，通常形如：
```python
user_record = ClawMessage(
    conversation_id=str(conv_id),
    role=MessageRole.USER,
    content=user_message,
    ...
)
```

**Step 3: 修改用户消息保存逻辑**

将保存用户消息时 `content=user_message` 改为只存文本部分，并在有图片时写 `extra_data`：

```python
image_count = _count_images(user_message)
user_record = ClawMessage(
    conversation_id=str(conv_id),
    role=MessageRole.USER,
    content=_extract_text_content(user_message),
    extra_data={"has_images": True, "image_count": image_count} if image_count > 0 else {},
)
```

**Step 4: 确认 Agent 输入透传**

找到 `input_data = {"messages": [{"role": "user", "content": user_message}]}` 这一行，确认 `user_message` 就是原始的 `str | list`，无需修改。LangChain `HumanMessage` 会自动处理 list content。

**Step 5: 错误处理 — 视觉不支持时友好提示**

在 `chat_event_generator` 的主 `except` 块（捕获 agent stream 异常的地方）中，添加对视觉相关错误的检测：

```python
except Exception as exc:
    error_msg = str(exc).lower()
    vision_keywords = ["vision", "image", "multimodal", "does not support", "unsupported"]
    if any(kw in error_msg for kw in vision_keywords) and _count_images(user_message) > 0:
        friendly_msg = (
            "当前模型不支持图片识别，请在对话设置中切换到支持视觉的模型"
            "（如 claude-3-5-sonnet、gpt-4o）"
        )
        yield _sse_event("error", message=friendly_msg)
    else:
        yield _sse_event("error", message=str(exc))
    return
```

注意：需要找到现有 `_sse_event` 函数的调用签名，确保参数一致。

**Step 6: 找到 chat endpoint，确认 `user_message` 变量取自 `data.content`**

搜索 `@router.post` 的 chat endpoint，确认：
```python
user_message = data.content  # 此时类型为 str | list
```
若有 `str(data.content)` 等强制转字符串的代码，需要去掉。

**Step 7: 验证**

```bash
cd javisagent/backend && python -c "
from src.routes.claw.chat import _extract_text_content, _count_images
assert _extract_text_content('hello') == 'hello'
assert _extract_text_content([{'type':'text','text':'hi'}, {'type':'image_url','image_url':{'url':'data:...'}}]) == 'hi'
assert _count_images([{'type':'image_url','image_url':{'url':'x'}}]) == 1
print('OK')
"
```
Expected: `OK`

**Step 8: Commit**

```bash
git add javisagent/backend/src/routes/claw/chat.py
git commit -m "feat(claw): support multimodal content in chat - extract text for DB, pass list to agent"
```

---

## Task 3: 前端 TypeScript 类型定义

**Files:**
- Modify: `javisagent/frontend/src/types/claw.ts`

**Step 1: 新增多模态类型**

在 `claw.ts` 文件顶部（`export interface ClawConversation` 之前）新增：

```typescript
export interface TextContentBlock {
  type: "text";
  text: string;
}

export interface ImageContentBlock {
  type: "image_url";
  image_url: { url: string }; // data:image/xxx;base64,...
}

export type ContentBlock = TextContentBlock | ImageContentBlock;
```

**Step 2: 修改 `MessageCreate` 类型**

找到 `MessageCreate`（在 `clawApi.ts` 或 `claw.ts` 中），将 `content` 字段改为：

```typescript
export interface MessageCreate {
  content: string | ContentBlock[];
  selected_skill?: string | null;
}
```

如果 `MessageCreate` 定义在 `clawApi.ts` 中，同样修改。

**Step 3: TypeScript 编译检查**

```bash
cd javisagent/frontend && npx tsc --noEmit 2>&1 | head -30
```
Expected: 无错误或仅有与本次修改无关的已有错误

**Step 4: Commit**

```bash
git add javisagent/frontend/src/types/claw.ts javisagent/frontend/src/services/clawApi.ts
git commit -m "feat(claw): add ContentBlock types for multimodal message support"
```

---

## Task 4: 前端图片上传状态与工具函数

**Files:**
- Modify: `javisagent/frontend/src/pages/ClawChatPage.tsx`

**Step 1: 新增图片状态**

在 `ClawChatPage` 组件状态声明区（`inputValue` 附近）新增：

```typescript
const [attachedImages, setAttachedImages] = useState<string[]>([]); // base64 data URLs
const fileInputRef = useRef<HTMLInputElement | null>(null);
```

**Step 2: 新增图片读取工具函数**

在组件内（或组件外作为纯函数）新增：

```typescript
function readFileAsDataURL(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}
```

**Step 3: 新增图片处理函数**

```typescript
const handleImageFiles = useCallback(async (files: FileList | File[]) => {
  const fileArray = Array.from(files).filter((f) => f.type.startsWith("image/"));
  if (fileArray.length === 0) return;

  const remaining = 4 - attachedImages.length;
  if (remaining <= 0) {
    message.warning("最多上传 4 张图片");
    return;
  }

  const toProcess = fileArray.slice(0, remaining);
  const oversized = toProcess.filter((f) => f.size > 10 * 1024 * 1024);
  if (oversized.length > 0) {
    message.error(`图片大小不能超过 10MB（${oversized.map((f) => f.name).join(", ")}）`);
    return;
  }

  try {
    const dataUrls = await Promise.all(toProcess.map(readFileAsDataURL));
    setAttachedImages((prev) => [...prev, ...dataUrls].slice(0, 4));
  } catch {
    message.error("图片读取失败");
  }
}, [attachedImages.length]);
```

**Step 4: 新增粘贴处理**

在输入框 `<Input.TextArea>` 上添加 `onPaste` 处理：

```typescript
const handlePaste = useCallback(
  (e: React.ClipboardEvent) => {
    const items = Array.from(e.clipboardData.items);
    const imageItems = items.filter((item) => item.type.startsWith("image/"));
    if (imageItems.length === 0) return;
    e.preventDefault();
    const files = imageItems.map((item) => item.getAsFile()).filter(Boolean) as File[];
    void handleImageFiles(files);
  },
  [handleImageFiles],
);
```

**Step 5: 修改 content 构建逻辑（`buildContent` 函数）**

找到发送消息的 `handleSend`（或类似函数），修改构建 content 的部分：

```typescript
const buildContent = (): string | ContentBlock[] => {
  if (attachedImages.length === 0) {
    return inputValue;
  }
  const blocks: ContentBlock[] = [];
  if (inputValue.trim()) {
    blocks.push({ type: "text", text: inputValue });
  }
  attachedImages.forEach((url) => {
    blocks.push({ type: "image_url", image_url: { url } });
  });
  return blocks;
};
```

在发送成功后（`setInputValue("")` 附近）清空图片：
```typescript
setAttachedImages([]);
```

**Step 6: TypeScript 检查**

```bash
cd javisagent/frontend && npx tsc --noEmit 2>&1 | head -30
```

**Step 7: Commit**

```bash
git add javisagent/frontend/src/pages/ClawChatPage.tsx
git commit -m "feat(claw): add image attachment state and file handling logic"
```

---

## Task 5: 前端输入区 UI — 上传按钮与缩略图预览

**Files:**
- Modify: `javisagent/frontend/src/pages/ClawChatPage.tsx`

**Step 1: 新增隐藏文件输入**

在 JSX 的发送按钮区域附近（输入框下方的 div 中）添加隐藏 file input：

```tsx
<input
  ref={fileInputRef}
  type="file"
  accept="image/png,image/jpeg,image/gif,image/webp"
  multiple
  style={{ display: "none" }}
  onChange={(e) => {
    if (e.target.files) {
      void handleImageFiles(e.target.files);
      e.target.value = ""; // 允许重复选同一文件
    }
  }}
/>
```

**Step 2: 新增图片按钮（在发送按钮旁边）**

找到输入框底部工具栏（发送按钮所在区域），在 `SendOutlined` 按钮前添加：

```tsx
<Tooltip title="上传图片（最多4张）">
  <Button
    icon={<PaperClipOutlined />}
    size="small"
    type="text"
    onClick={() => fileInputRef.current?.click()}
    disabled={attachedImages.length >= 4}
  />
</Tooltip>
```

同时在 import 中添加 `PaperClipOutlined`（来自 `@ant-design/icons`）。

**Step 3: 缩略图预览行**

在 `<Input.TextArea>` 上方（或输入区容器内）插入预览行，仅在有图片时渲染：

```tsx
{attachedImages.length > 0 && (
  <div style={{ display: "flex", gap: 8, flexWrap: "wrap", padding: "8px 0 4px" }}>
    {attachedImages.map((url, idx) => (
      <div key={idx} style={{ position: "relative", display: "inline-block" }}>
        <img
          src={url}
          alt={`附件${idx + 1}`}
          style={{
            width: 64,
            height: 64,
            objectFit: "cover",
            borderRadius: 6,
            border: "1px solid #d9d9d9",
          }}
        />
        <Button
          size="small"
          type="text"
          icon={<CloseCircleOutlined />}
          style={{
            position: "absolute",
            top: -8,
            right: -8,
            color: "#ff4d4f",
            padding: 0,
            minWidth: 20,
            height: 20,
            lineHeight: "20px",
          }}
          onClick={() => setAttachedImages((prev) => prev.filter((_, i) => i !== idx))}
        />
      </div>
    ))}
  </div>
)}
```

`CloseCircleOutlined` 已在项目中 import，确认即可。

**Step 4: 在 `Input.TextArea` 上添加 onPaste**

```tsx
<Input.TextArea
  ...
  onPaste={handlePaste}
/>
```

**Step 5: 前端开发服务器验证**

```bash
cd javisagent/frontend && npm run dev
```

打开浏览器验证：
- 点击回形针图标能弹出文件选择框
- 选择图片后出现缩略图预览
- 点击 × 可以删除单张图片
- Ctrl+V 粘贴截图可以添加到预览

**Step 6: Commit**

```bash
git add javisagent/frontend/src/pages/ClawChatPage.tsx
git commit -m "feat(claw): add image upload button, thumbnail preview, and paste support"
```

---

## Task 6: 前端消息气泡 — 图片展示与历史占位

**Files:**
- Modify: `javisagent/frontend/src/pages/ClawChatPage.tsx`
- Modify: `javisagent/frontend/src/pages/clawTimeline.ts`

**Step 1: Timeline 用户消息携带图片信息**

查看 `clawTimeline.ts` 中用户消息 timeline item 的类型定义（通常是 `kind: "user"` 的 item）。如果该 item 有 `content` 字段，新增可选 `images?: string[]` 字段：

```typescript
export interface UserTimelineItem {
  id: string;
  kind: "user";
  content: string;
  images?: string[];       // 新增：发送时的图片 base64 URLs
  hasHistoryImages?: boolean; // 新增：历史消息含图片占位
  imageCount?: number;
  selectedSkill?: string | null;
  promptDebug?: PromptDebugSnapshot | null;
  isStreaming?: boolean;
}
```

**Step 2: 发送消息时把图片传入 timeline item**

在 `handleSend`（发送消息的函数）中，构建 timeline user item 时传入当前图片：

```typescript
applyTimelineAction(currentConvId, {
  type: "add_user",
  content: inputValue,
  images: attachedImages.length > 0 ? [...attachedImages] : undefined,
  // ... 其他字段
});
```

（具体 action type 和字段名以 `clawTimeline.ts` 实际定义为准）

**Step 3: 历史消息加载时处理占位**

在 `buildHistoryTimeline`（`clawTimeline.ts`）中，处理 user 消息时检查 `metadata.has_images`：

```typescript
if (msg.role === "user") {
  items.push({
    id: msg.id,
    kind: "user",
    content: msg.content,
    hasHistoryImages: (msg.metadata as any)?.has_images === true,
    imageCount: (msg.metadata as any)?.image_count,
    // ...
  });
}
```

**Step 4: 用户气泡渲染新增图片展示**

在 `renderTimelineItem` 中，用户消息气泡（`item.kind === "user"`）的文字内容下方添加：

```tsx
{/* 实时发送时的图片预览 */}
{item.images && item.images.length > 0 && (
  <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 8 }}>
    {item.images.map((url, idx) => (
      <img
        key={idx}
        src={url}
        alt={`图片${idx + 1}`}
        style={{
          width: 100,
          height: 100,
          objectFit: "cover",
          borderRadius: 6,
          border: "1px solid #d9d9d9",
          cursor: "pointer",
        }}
        onClick={() => window.open(url, "_blank")}
      />
    ))}
  </div>
)}
{/* 历史消息图片占位 */}
{item.hasHistoryImages && (
  <div style={{ marginTop: 8, color: "#8c8c8c", fontSize: 12 }}>
    🖼 [图片 × {item.imageCount ?? 1}]（图片内容不在历史记录中保存）
  </div>
)}
```

**Step 5: TypeScript 检查**

```bash
cd javisagent/frontend && npx tsc --noEmit 2>&1 | head -30
```

**Step 6: Commit**

```bash
git add javisagent/frontend/src/pages/ClawChatPage.tsx javisagent/frontend/src/pages/clawTimeline.ts
git commit -m "feat(claw): render images in user message bubbles and show history placeholder"
```

---

## Task 7: 端到端手动验证

**Step 1: 启动后端**

```bash
conda activate lcv1 ; cd javisagent/backend && python src/main.py
```

**Step 2: 启动前端**

```bash
cd javisagent/frontend && npm run dev
```

**Step 3: 验证清单**

- [ ] 纯文本消息发送正常（向后兼容）
- [ ] 点击回形针上传图片，缩略图正确显示
- [ ] Ctrl+V 粘贴截图出现在预览中
- [ ] 超过 4 张时出现警告，不允许继续添加
- [ ] 发送含图片的消息后，模型返回图片内容描述
- [ ] 发送后图片预览清空
- [ ] 刷新页面重新加载历史消息，含图片的消息显示占位提示
- [ ] 使用不支持视觉的模型发送图片时，出现友好错误提示

**Step 4: 最终 Commit**

```bash
git add -p  # 检查没有遗漏的修改
git commit -m "feat(claw): complete image upload feature for multimodal chat"
```
