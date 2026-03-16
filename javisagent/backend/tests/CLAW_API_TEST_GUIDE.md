# Claw API 测试指南

## 启动服务

```bash
cd javisagent/backend
python src/main.py
```

服务将在 `http://localhost:8000` 启动。

API 文档：`http://localhost:8000/docs`

## API 端点

### 1. 验证工作目录

**POST** `/api/claw/validate-directory`

```bash
curl -X POST http://localhost:8000/api/claw/validate-directory \
  -H "Content-Type: application/json" \
  -d '{"path": "/tmp"}'
```

响应：
```json
{
  "valid": true,
  "reason": null
}
```

### 2. 获取可用模型列表

**GET** `/api/claw/models`

```bash
curl http://localhost:8000/api/claw/models
```

响应：
```json
{
  "models": [
    {
      "model_id": "claude-opus-4-6",
      "name": "Claude Opus 4.6",
      "provider": "Anthropic"
    },
    {
      "model_id": "claude-sonnet-4-6",
      "name": "Claude Sonnet 4.6",
      "provider": "Anthropic"
    },
    {
      "model_id": "gpt-4o",
      "name": "GPT-4o",
      "provider": "OpenAI"
    },
    {
      "model_id": "gpt-4o-mini",
      "name": "GPT-4o Mini",
      "provider": "OpenAI"
    }
  ]
}
```

### 3. 创建对话

**POST** `/api/claw/conversations`

```bash
curl -X POST http://localhost:8000/api/claw/conversations \
  -H "Content-Type: application/json" \
  -d '{
    "working_directory": "/tmp",
    "title": "测试对话",
    "llm_model": "claude-opus-4-6"
  }'
```

响应：
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "测试对话",
  "working_directory": "/tmp",
  "llm_model": "claude-opus-4-6",
  "created_at": "2026-03-10T10:00:00",
  "updated_at": "2026-03-10T10:00:00"
}
```

### 4. 获取对话列表

**GET** `/api/claw/conversations`

```bash
curl http://localhost:8000/api/claw/conversations
```

响应：
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "测试对话",
    "working_directory": "/tmp",
    "llm_model": "claude-opus-4-6",
    "created_at": "2026-03-10T10:00:00",
    "updated_at": "2026-03-10T10:00:00"
  }
]
```

### 5. 获取对话详情

**GET** `/api/claw/conversations/{conv_id}`

```bash
curl http://localhost:8000/api/claw/conversations/550e8400-e29b-41d4-a716-446655440000
```

响应：同创建对话的响应格式

### 6. 更新对话

**PUT** `/api/claw/conversations/{conv_id}`

```bash
curl -X PUT http://localhost:8000/api/claw/conversations/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "更新后的标题",
    "llm_model": "gpt-4o"
  }'
```

响应：更新后的对话对象

### 7. 删除对话

**DELETE** `/api/claw/conversations/{conv_id}`

```bash
curl -X DELETE http://localhost:8000/api/claw/conversations/550e8400-e29b-41d4-a716-446655440000
```

响应：
```json
{
  "message": "删除成功"
}
```

## 错误处理

### 无效的工作目录

```bash
curl -X POST http://localhost:8000/api/claw/conversations \
  -H "Content-Type: application/json" \
  -d '{
    "working_directory": "/nonexistent",
    "title": "测试"
  }'
```

响应（400 错误）：
```json
{
  "detail": "无效的工作目录: 目录不存在"
}
```

### 对话不存在

```bash
curl http://localhost:8000/api/claw/conversations/00000000-0000-0000-0000-000000000000
```

响应（404 错误）：
```json
{
  "detail": "对话不存在"
}
```

## 自动化测试

运行测试脚本：

```bash
cd javisagent/backend
python tests/test_claw_api.py
```

测试脚本将自动执行所有 CRUD 操作并验证结果。

## 注意事项

1. 工作目录必须存在且可读
2. 对话 ID 使用 UUID 格式
3. 所有时间戳使用 ISO 8601 格式
4. 对话列表按更新时间倒序排列
5. 删除对话会级联删除相关的消息和工具调用记录
