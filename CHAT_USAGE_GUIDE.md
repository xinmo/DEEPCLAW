# JavisClaw 对话功能使用指南

## 功能概述

JavisClaw 智能体管理平台现已支持完整的用户对话与消息管理功能，包括：

- ✅ 实时对话界面 - 支持用户与智能体进行多轮对话
- ✅ 消息持久化 - 保存完整的对话历史记录
- ✅ 会话管理 - 支持多会话切换和管理
- ✅ 流式响应 - 使用 SSE 实现打字机效果
- ✅ 富文本支持 - 支持 Markdown 渲染、代码高亮、文件上传

## 快速开始

### 1. 启动后端服务

```bash
cd javisagent/backend
python src/main.py
```

后端服务将在 `http://localhost:8000` 启动。

### 2. 启动前端服务

```bash
cd javisagent/frontend
npm run dev
```

前端服务将在 `http://localhost:5173` 启动。

### 3. 配置环境变量

在 `javisagent/backend/.env` 文件中配置 LLM API 密钥：

```env
# OpenAI
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1

# Anthropic Claude
ANTHROPIC_API_KEY=your_anthropic_api_key

# DeepSeek
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com

# 智谱 AI
ZHIPU_API_KEY=your_zhipu_api_key

# 阿里通义
DASHSCOPE_API_KEY=your_dashscope_api_key
```

## 使用流程

### 1. 创建智能体

1. 在左侧菜单点击 **JavisClaw > 智能体管理**
2. 点击 **创建智能体** 按钮（功能待实现，目前需要通过 API 创建）
3. 配置智能体的名称、描述、LLM 提供商、模型等参数

### 2. 开始对话

1. 在智能体列表中找到目标智能体
2. 点击 **对话** 按钮
3. 系统会自动创建新会话并跳转到对话界面

### 3. 发送消息

1. 在输入框中输入消息
2. 按 **Enter** 发送（Shift+Enter 换行）
3. 智能体会以流式方式逐字返回回复

### 4. 管理会话

- **新建会话**：点击左侧 **新建会话** 按钮
- **切换会话**：点击左侧会话列表中的会话
- **删除会话**：点击会话右侧的删除按钮

### 5. 高级功能

#### 上传文件
1. 点击输入框下方的 **附件** 按钮
2. 选择要上传的文件（支持图片、PDF、文档等）
3. 文件会随消息一起发送给智能体

#### 复制消息
- 点击消息下方的 **复制** 按钮

#### 重新生成
- 点击消息下方的 **重新生成** 按钮

#### 停止生成
- 在智能体回复过程中，点击 **停止** 按钮

## API 端点

### 会话管理

```bash
# 创建会话
POST /api/javisclaw/chat/sessions
Body: { "agent_id": "agent_id" }

# 获取会话列表
GET /api/javisclaw/chat/sessions?agent_id=xxx&limit=20&offset=0

# 删除会话
DELETE /api/javisclaw/chat/sessions/{session_id}
```

### 消息管理

```bash
# 获取消息列表
GET /api/javisclaw/chat/messages?session_id=xxx&limit=50&offset=0

# 发送消息（流式响应）
POST /api/javisclaw/chat/stream
Body: { "session_id": "xxx", "message": "Hello" }
Response: SSE Stream
```

### 文件上传

```bash
# 上传文件
POST /api/javisclaw/chat/upload
Content-Type: multipart/form-data
Body: { "file": File }
```

## 支持的 LLM 提供商

| 提供商 | 模型示例 | 环境变量 |
|--------|----------|----------|
| OpenAI | gpt-4o, gpt-4o-mini | OPENAI_API_KEY |
| Anthropic | claude-3-5-sonnet-20241022 | ANTHROPIC_API_KEY |
| DeepSeek | deepseek-chat | DEEPSEEK_API_KEY |
| 智谱 AI | glm-4, glm-4-flash | ZHIPU_API_KEY |
| 阿里通义 | qwen-max, qwen-plus | DASHSCOPE_API_KEY |

## 数据库结构

### chat_sessions 表
- `id`: 会话 ID (UUID)
- `agent_id`: 智能体 ID
- `title`: 会话标题
- `created_at`: 创建时间
- `updated_at`: 更新时间

### chat_messages 表
- `id`: 消息 ID (UUID)
- `session_id`: 会话 ID
- `role`: 角色 (user/assistant/system/tool)
- `content`: 消息内容
- `model`: 使用的模型
- `tokens_used`: Token 消耗
- `tool_calls`: 工具调用记录
- `created_at`: 创建时间

### message_attachments 表
- `id`: 附件 ID (UUID)
- `message_id`: 消息 ID
- `file_name`: 文件名
- `file_path`: 文件路径
- `file_type`: 文件类型
- `file_size`: 文件大小
- `created_at`: 创建时间

## 故障排查

### 1. 无法连接到后端
- 检查后端服务是否启动
- 检查端口 8000 是否被占用
- 检查防火墙设置

### 2. LLM 调用失败
- 检查 API 密钥是否正确配置
- 检查网络连接
- 检查 API 配额是否用尽

### 3. 消息无法发送
- 检查会话是否存在
- 检查智能体配置是否正确
- 查看浏览器控制台错误信息

### 4. 流式响应中断
- 检查网络连接稳定性
- 检查 SSE 连接是否被代理服务器阻断
- 尝试刷新页面重新连接

## 下一步计划

- [ ] 语音输入/输出
- [ ] 多人协作对话
- [ ] 对话分享/导出功能
- [ ] 智能体主动推送消息
- [ ] 对话搜索功能
- [ ] 消息标注和反馈
- [ ] 对话统计和分析

## 技术支持

如有问题，请查看：
- 后端日志：`javisagent/backend/logs/`
- 浏览器控制台：F12 打开开发者工具
- API 文档：`http://localhost:8000/docs`
