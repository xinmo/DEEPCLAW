# Claw Chat 图片上传功能设计文档

**日期：** 2026-03-20
**状态：** 已批准
**作者：** Claude Opus 4.6

---

## 背景与目标

当前对话龙虾（Claw Chat）只支持纯文本输入。本次设计目标是让用户可以在对话中上传图片，由智能体（视觉模型）识别图片内容并回答提问，体验类似 DeepSeek 官网、Claude.ai 等编程助手。

**约束：**
- 图片仅用 base64 传输，不落盘、不入库（重开历史对话后图片不可复现）
- 不强制绑定特定视觉模型，当前选择的模型支持视觉即生效，不支持时给出友好提示

---

## 方案选择

采用**方案 A：扩展 content 字段为多模态块格式**。

理由：
1. LangChain `HumanMessage(content=[...])` 原生支持多模态 list 格式，改动最小
2. 复用 OpenAI Vision / Anthropic Vision 统一格式，无需为每个 provider 单独适配
3. 向后兼容：纯文本消息 content 仍为 `str`，不影响现有流程

---

## 数据结构与协议

### 消息格式（`MessageCreate`）

纯文本消息（向后兼容，不变）：
```json
{
  "content": "你好",
  "selected_skill": null
}
```

含图片的多模态消息：
```json
{
  "content": [
    {"type": "text", "text": "这张截图有什么问题？"},
    {"type": "image_url", "image_url": {"url": "data:image/png;base64,..{base64}..."}}
  ],
  "selected_skill": null
}
```

支持多张图片（最多 4 张）：
```json
{
  "content": [
    {"type": "text", "text": "对比这两张图"},
    {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}},
    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
  ]
}
```

### 数据库存储

- `ClawMessage.content`（`Text` 字段）：只存文本部分，图片 base64 **不落库**
- `ClawMessage.extra_data`：当消息含图片时，写入 `{"has_images": true, "image_count": N}`，供前端在历史消息中展示占位提示

---

## 后端设计

### 1. Schema 变更（`schemas/claw.py`）

```python
class MessageCreate(BaseModel):
    content: str | list  # 原来是 str，现在支持多模态 list
    selected_skill: str | None = None
```

### 2. 文本提取工具函数（`routes/claw/chat.py`）

新增辅助函数，用于从 content（str 或 list）中提取纯文本以存入数据库：

```python
def _extract_text_content(content: str | list) -> str:
    if isinstance(content, str):
        return content
    parts = [
        block["text"]
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    return " ".join(parts) or "[图片]"

def _count_images(content: str | list) -> int:
    if isinstance(content, str):
        return 0
    return sum(
        1 for block in content
        if isinstance(block, dict) and block.get("type") == "image_url"
    )
```

### 3. `chat_event_generator` 改动

- **保存用户消息到 DB**：使用 `_extract_text_content(content)` 提取文本存 `content` 字段；若有图片，写 `extra_data={"has_images": True, "image_count": N}`
- **Agent 输入**：`content`（str 或 list）直接透传给 LangGraph，LangChain 自动转换为对应模型的多模态格式
- **错误处理**：在 SSE 流 `except` 块中，检测错误信息是否包含 `vision`、`image`、`multimodal`、`does not support` 等关键词，若是则返回友好 SSE error 事件："当前模型不支持图片识别，请在对话设置中切换到支持视觉的模型（如 claude-3-5-sonnet、gpt-4o）"

### 4. 历史消息返回（`get_messages`）

历史消息中图片内容不可复现。返回时保持现有结构，`content` 字段为纯文本。前端根据 `extra_data.has_images` 展示图片占位提示。

---

## 前端设计

### 1. 类型定义（`types/claw.ts`）

```typescript
export interface ImageContentBlock {
  type: "image_url";
  image_url: { url: string }; // data:image/xxx;base64,...
}

export interface TextContentBlock {
  type: "text";
  text: string;
}

export type ContentBlock = TextContentBlock | ImageContentBlock;

export interface MessageCreate {
  content: string | ContentBlock[];
  selected_skill?: string | null;
}
```

### 2. 输入区 UI 改动（`ClawChatPage.tsx`）

**新增状态：**
```typescript
const [attachedImages, setAttachedImages] = useState<string[]>([]); // base64 url 列表
```

**图片上传入口：**
- 输入框左侧添加 `PaperClipOutlined` 图标按钮
- 点击触发隐藏的 `<input type="file" accept="image/png,image/jpeg,image/gif,image/webp" multiple>`
- 最多 4 张，超出时提示用户
- 每张图片大小上限 10MB（前端校验，防止 base64 过大导致请求失败）

**粘贴支持：**
- 在输入框 `onPaste` 事件中检测 `clipboardData.items`，如有 `image/*` 类型则读取为 base64

**缩略图预览行：**
- 图片选中后，在输入框上方显示一行缩略图（`64×64px`，`object-fit: cover`，圆角）
- 每张右上角显示 × 删除按钮
- 预览行仅在有图片时出现

**发送逻辑：**
```typescript
const buildContent = (): string | ContentBlock[] => {
  if (attachedImages.length === 0) {
    return inputValue; // 纯文本，向后兼容
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
发送后清空 `attachedImages`。

### 3. 消息气泡展示

**实时流（发送时）：**
- 用户消息气泡中，附带图片时在文字下方展示缩略图行（来自本地 `attachedImages` state，发送前缓存）

**历史消息（重新加载时）：**
- 若 `extra_data.has_images === true`，在消息气泡中文字下方展示灰色占位区：
  ```
  🖼 [图片 × N]（图片内容不在历史记录中保存）
  ```

### 4. API 调用（`services/clawApi.ts`）

`sendMessage` 函数无需改动，`body: JSON.stringify(message)` 已自动序列化 list content。

---

## 改动范围汇总

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| `backend/src/schemas/claw.py` | 修改 | `content: str → str \| list` |
| `backend/src/routes/claw/chat.py` | 修改 | 新增文本提取函数，改造用户消息保存逻辑，错误处理 |
| `frontend/src/types/claw.ts` | 修改 | 新增 `ContentBlock` 类型，`MessageCreate.content` 改为联合类型 |
| `frontend/src/pages/ClawChatPage.tsx` | 修改 | 图片上传按钮、预览、粘贴、发送逻辑、气泡展示 |
| `frontend/src/services/clawApi.ts` | 不变 | JSON 序列化已支持 |

---

## 不在范围内

- 图片持久化存储（明确不做）
- 图片 OCR 后结构化提取（未来可扩展）
- 视频/音频上传（未来可扩展）
- 压缩大图片（前端 10MB 限制代替）
