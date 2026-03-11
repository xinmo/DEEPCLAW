# 提示词管理功能设计文档

**日期：** 2026-03-11
**功能：** Claw 智能体提示词管理
**版本：** 1.0

## 概述

为 JAVISAGENT 的 Claw 模块添加提示词管理功能，允许用户通过 Web 界面查看和编辑系统提示词。用户修改后的提示词将在新创建的对话中生效，现有对话保持不变。

## 需求

### 功能需求

1. **提示词查看**：用户可以查看当前的系统提示词内容
2. **提示词编辑**：用户可以编辑系统提示词
3. **提示词保存**：用户可以保存修改后的提示词
4. **提示词重置**：用户可以将提示词重置为默认值
5. **生效机制**：修改后的提示词仅对新创建的对话生效，现有对话不受影响

### 非功能需求

1. **易用性**：界面简洁直观，支持多行文本编辑
2. **可扩展性**：架构支持未来添加更多类型的提示词管理
3. **数据一致性**：每个对话独立保存提示词，确保历史对话不受影响
4. **错误处理**：妥善处理文件读写失败、空内容等异常情况

## 技术方案

### 方案选择

采用 **配置文件 + 前端缓存** 方案：

- 提示词存储在配置文件 `javisagent/backend/config/system_prompt.txt`
- 每个对话创建时将当前提示词保存到数据库
- 对话进行时使用数据库中保存的提示词

**优点：**
- 实现简单，配置文件易于备份和版本控制
- 每个对话独立保存提示词，历史对话不受影响
- 支持未来扩展多个提示词类型

## 架构设计

### 数据库设计

**修改 ClawConversation 模型：**

```python
# javisagent/backend/src/models/claw.py

class ClawConversation(Base):
    __tablename__ = 'claw_conversations'
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    working_directory = Column(String, nullable=False)
    llm_model = Column(String, nullable=False, default='claude-opus-4-6')
    system_prompt = Column(Text, nullable=True)  # 新增字段
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**迁移策略：**
- SQLAlchemy 会自动添加新列（因为使用了 `extend_existing=True`）
- 现有对话的 `system_prompt` 字段为 NULL，使用时回退到默认提示词

### 后端 API 设计

**新增路由文件：** `javisagent/backend/src/routes/claw/prompts.py`

**API 端点：**

```
GET /api/claw/prompts
# 获取所有可管理的提示词列表
# 响应: {
#   "prompts": [
#     {
#       "id": "system_prompt",
#       "name": "系统提示词",
#       "description": "Claw 智能体的默认系统提示词"
#     }
#   ]
# }

GET /api/claw/prompts/{prompt_id}
# 获取指定提示词的详细内容
# 响应: {
#   "id": "system_prompt",
#   "name": "系统提示词",
#   "content": "...",
#   "default_content": "..."
# }

PUT /api/claw/prompts/{prompt_id}
# 更新指定提示词
# 请求体: { "content": "..." }
# 响应: { "success": true, "message": "保存成功" }

POST /api/claw/prompts/{prompt_id}/reset
# 重置为默认提示词
# 响应: { "success": true, "content": "..." }
```

**配置文件结构：**

- 默认提示词：硬编码在 `agent.py` 的 `SYSTEM_PROMPT_TEMPLATE` 中
- 用户自定义提示词：保存到 `javisagent/backend/config/system_prompt.txt`
- 读取逻辑：优先读取配置文件，如果不存在则使用默认提示词

**修改对话创建逻辑：**

在 `javisagent/backend/src/routes/claw/conversations.py` 中：

```python
@router.post("/conversations")
async def create_conversation(request: ConversationCreateRequest, db: Session = Depends(get_db)):
    # 读取当前系统提示词
    current_prompt = get_current_system_prompt()

    # 创建对话
    conversation = ClawConversation(
        title=request.title,
        working_directory=request.working_directory,
        llm_model=request.llm_model,
        system_prompt=current_prompt  # 保存当前提示词
    )
    db.add(conversation)
    db.commit()
    return conversation
```

### 前端设计

**新增页面：** `javisagent/frontend/src/pages/PromptManagementPage.tsx`

**页面布局：**

```
┌─────────────────────────────────────────────────┐
│  提示词管理                                      │
├──────────────┬──────────────────────────────────┤
│              │  系统提示词                       │
│  系统提示词  │  ┌────────────────────────────┐  │
│  (选中状态)  │  │                            │  │
│              │  │  TextArea 编辑器            │  │
│              │  │  (多行文本输入框)           │  │
│              │  │                            │  │
│              │  └────────────────────────────┘  │
│              │  [保存] [重置为默认]              │
└──────────────┴──────────────────────────────────┘
```

**组件结构：**

- 使用 Ant Design 的 `Layout.Sider` + `Layout.Content`
- 左侧：`Menu` 组件显示提示词列表
- 右侧：
  - 标题显示当前选中的提示词名称
  - `Input.TextArea` 组件（`rows={20}`, `autoSize`）
  - 底部操作按钮：保存、重置为默认

**交互逻辑：**

1. 页面加载时调用 `GET /api/claw/prompts` 获取提示词列表
2. 默认选中第一个提示词，调用 `GET /api/claw/prompts/{id}` 获取详情
3. 用户编辑后点击"保存"，调用 `PUT /api/claw/prompts/{id}`
4. 点击"重置为默认"，调用 `POST /api/claw/prompts/{id}/reset`
5. 保存成功后显示 `message.success("保存成功，新对话将使用此提示词")`

**路由和菜单集成：**

在 `SideMenu.tsx` 中添加子菜单项：

```typescript
{
  key: 'claw',
  icon: <MessageOutlined />,
  label: 'Claw',
  children: [
    {
      key: 'claw-chat',
      label: '对话龙虾',
    },
    {
      key: 'prompt-management',
      label: '提示词管理',
    },
  ],
}
```

在 `App.tsx` 中添加路由：

```typescript
<Route path="/claw/prompt-management" element={<PromptManagementPage />} />
```

**新增 API 服务：** `javisagent/frontend/src/services/promptApi.ts`

```typescript
export const promptApi = {
  getPrompts: () => api.get('/claw/prompts'),
  getPromptDetail: (id: string) => api.get(`/claw/prompts/${id}`),
  updatePrompt: (id: string, content: string) =>
    api.put(`/claw/prompts/${id}`, { content }),
  resetPrompt: (id: string) =>
    api.post(`/claw/prompts/${id}/reset`),
};
```

## 数据流

### 提示词修改流程

```
用户编辑提示词
    ↓
点击"保存"按钮
    ↓
前端调用 PUT /api/claw/prompts/{id}
    ↓
后端写入 config/system_prompt.txt
    ↓
返回成功响应
    ↓
前端显示成功提示
```

### 新对话创建流程

```
用户创建新对话
    ↓
前端调用 POST /api/claw/conversations
    ↓
后端读取 config/system_prompt.txt
    ↓
保存到 ClawConversation.system_prompt
    ↓
返回对话信息
```

### 对话进行流程

```
用户发送消息
    ↓
前端调用 POST /api/claw/conversations/{id}/chat
    ↓
后端从 ClawConversation.system_prompt 读取提示词
    ↓
如果为 NULL，使用默认提示词
    ↓
传递给 create_deep_agent
    ↓
返回 SSE 流式响应
```

## 错误处理

### 配置文件读写失败

- **场景**：文件权限不足、磁盘空间不足
- **处理**：捕获 IO 异常，返回 500 错误
- **前端**：显示 `message.error("保存失败，请检查服务器权限")`

### 配置文件不存在

- **场景**：首次使用或文件被删除
- **处理**：自动回退到默认提示词
- **首次保存**：自动创建 `config/` 目录和文件

### 提示词为空

- **前端验证**：保存前检查内容不为空
- **后端验证**：拒绝空内容，返回 400 错误
- **前端**：显示 `message.error("提示词不能为空")`

### 并发修改

- **初期**：不处理并发修改（文件系统自然覆盖）
- **未来**：可选实现文件锁或时间戳检查

## 生效机制

### 新对话生效

- 用户保存提示词后，只有新创建的对话使用新提示词
- 现有对话继续使用创建时保存的提示词
- 用户在保存成功提示中明确告知："保存成功，新对话将使用此提示词"

### 旧对话兼容

- 旧对话的 `system_prompt` 字段为 NULL
- 对话进行时检测到 NULL，自动使用默认提示词
- 确保旧对话不会因为缺少提示词而报错

## 扩展性

### 支持多个提示词类型

当前架构支持未来添加更多提示词类型：

1. **工具提示词**：用于指导工具使用的提示词
2. **角色提示词**：不同角色（如代码审查、文档编写）的提示词
3. **场景提示词**：特定场景（如调试、重构）的提示词

**实现方式：**

- 在 `config/` 目录下添加更多配置文件
- 在 API 中添加新的 `prompt_id`
- 在前端左侧菜单中添加新的列表项
- 在数据库中添加对应的字段（如 `tool_prompt`, `role_prompt`）

## 实现清单

### 后端任务

1. 修改 `ClawConversation` 模型，添加 `system_prompt` 字段
2. 创建 `javisagent/backend/src/routes/claw/prompts.py` 路由文件
3. 实现提示词读取、保存、重置逻辑
4. 修改对话创建接口，保存当前提示词
5. 修改对话聊天接口，使用对话的 `system_prompt` 字段
6. 在 `app.py` 中注册新路由

### 前端任务

1. 创建 `javisagent/frontend/src/pages/PromptManagementPage.tsx` 页面
2. 创建 `javisagent/frontend/src/services/promptApi.ts` API 服务
3. 修改 `SideMenu.tsx`，添加"提示词管理"菜单项
4. 修改 `App.tsx`，添加路由配置
5. 实现页面交互逻辑（加载、编辑、保存、重置）

### 测试任务

1. 测试提示词保存和读取
2. 测试新对话使用新提示词
3. 测试旧对话使用旧提示词
4. 测试重置为默认功能
5. 测试错误处理（空内容、文件读写失败）

## 总结

本设计采用配置文件 + 数据库的混合方案，实现了提示词管理功能。用户可以通过 Web 界面编辑系统提示词，修改后的提示词仅对新对话生效，确保历史对话不受影响。架构设计支持未来扩展更多类型的提示词管理。
