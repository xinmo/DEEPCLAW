# 提示词管理功能实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 Claw 智能体添加提示词管理功能，支持用户通过 Web 界面查看、编辑和保存系统提示词

**Architecture:** 配置文件 + 数据库混合方案。提示词存储在配置文件中，新对话创建时将当前提示词保存到数据库，确保每个对话独立使用创建时的提示词。

**Tech Stack:** Python FastAPI, SQLAlchemy, React, TypeScript, Ant Design

---

## Task 1: 修改数据库模型

**Files:**
- Modify: `javisagent/backend/src/models/claw.py:20-32`

**Step 1: 添加 system_prompt 字段到 ClawConversation 模型**

在 `ClawConversation` 类中添加新字段：

```python
system_prompt = Column(Text, nullable=True)  # 对话创建时使用的系统提示词
```

完整的字段列表应该是：
```python
id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
title = Column(String, nullable=False)
working_directory = Column(String, nullable=False)
llm_model = Column(String, nullable=False, default='claude-opus-4-6')
system_prompt = Column(Text, nullable=True)
created_at = Column(DateTime, default=datetime.utcnow)
updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Step 2: 验证模型修改**

运行后端服务，SQLAlchemy 会自动添加新列（因为使用了 `extend_existing=True`）

**Step 3: 提交更改**

```bash
git add javisagent/backend/src/models/claw.py
git commit -m "feat(backend): add system_prompt field to ClawConversation model"
```

---

## Task 2: 创建提示词管理路由

**Files:**
- Create: `javisagent/backend/src/routes/claw/prompts.py`

**Step 1: 创建路由文件并实现基础结构**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
import os

router = APIRouter()

# 配置文件路径
CONFIG_DIR = Path(__file__).parent.parent.parent.parent / "config"
SYSTEM_PROMPT_FILE = CONFIG_DIR / "system_prompt.txt"

# 从 agent.py 导入默认提示词
from ...services.claw.agent import SYSTEM_PROMPT_TEMPLATE


class PromptUpdateRequest(BaseModel):
    content: str


class PromptInfo(BaseModel):
    id: str
    name: str
    description: str


class PromptDetail(BaseModel):
    id: str
    name: str
    content: str
    default_content: str


def get_current_system_prompt() -> str:
    """读取当前系统提示词，优先从配置文件读取，不存在则使用默认"""
    if SYSTEM_PROMPT_FILE.exists():
        try:
            return SYSTEM_PROMPT_FILE.read_text(encoding='utf-8')
        except Exception as e:
            print(f"Error reading system prompt file: {e}")
            return SYSTEM_PROMPT_TEMPLATE
    return SYSTEM_PROMPT_TEMPLATE


@router.get("/prompts")
async def get_prompts():
    """获取所有可管理的提示词列表"""
    return {
        "prompts": [
            {
                "id": "system_prompt",
                "name": "系统提示词",
                "description": "Claw 智能体的默认系统提示词"
            }
        ]
    }


@router.get("/prompts/{prompt_id}")
async def get_prompt_detail(prompt_id: str):
    """获取指定提示词的详细内容"""
    if prompt_id != "system_prompt":
        raise HTTPException(status_code=404, detail="Prompt not found")

    current_content = get_current_system_prompt()

    return {
        "id": "system_prompt",
        "name": "系统提示词",
        "content": current_content,
        "default_content": SYSTEM_PROMPT_TEMPLATE
    }


@router.put("/prompts/{prompt_id}")
async def update_prompt(prompt_id: str, request: PromptUpdateRequest):
    """更新指定提示词"""
    if prompt_id != "system_prompt":
        raise HTTPException(status_code=404, detail="Prompt not found")

    if not request.content or not request.content.strip():
        raise HTTPException(status_code=400, detail="提示词不能为空")

    try:
        # 确保配置目录存在
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        # 写入配置文件
        SYSTEM_PROMPT_FILE.write_text(request.content, encoding='utf-8')

        return {"success": True, "message": "保存成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")


@router.post("/prompts/{prompt_id}/reset")
async def reset_prompt(prompt_id: str):
    """重置为默认提示词"""
    if prompt_id != "system_prompt":
        raise HTTPException(status_code=404, detail="Prompt not found")

    try:
        # 删除配置文件，回退到默认
        if SYSTEM_PROMPT_FILE.exists():
            SYSTEM_PROMPT_FILE.unlink()

        return {"success": True, "content": SYSTEM_PROMPT_TEMPLATE}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重置失败: {str(e)}")
```

**Step 2: 提交更改**

```bash
git add javisagent/backend/src/routes/claw/prompts.py
git commit -m "feat(backend): add prompt management API routes"
```

---

## Task 3: 注册提示词管理路由

**Files:**
- Modify: `javisagent/backend/src/app.py`

**Step 1: 导入并注册路由**

在导入部分添加：
```python
from src.routes.claw.prompts import router as claw_prompts_router
```

在路由注册部分添加：
```python
app.include_router(claw_prompts_router, prefix="/api/claw", tags=["claw-prompts"])
```

**Step 2: 提交更改**

```bash
git add javisagent/backend/src/app.py
git commit -m "feat(backend): register prompt management routes"
```

---

## Task 4: 修改对话创建接口

**Files:**
- Modify: `javisagent/backend/src/routes/claw/conversations.py`

**Step 1: 导入提示词读取函数**

在文件顶部添加导入：
```python
from .prompts import get_current_system_prompt
```

**Step 2: 修改创建对话的函数**

找到创建对话的函数（通常是 `POST /conversations` 端点），在创建 `ClawConversation` 对象时添加：

```python
# 读取当前系统提示词
current_prompt = get_current_system_prompt()

# 创建对话
conversation = ClawConversation(
    title=request.title,
    working_directory=request.working_directory,
    llm_model=request.llm_model,
    system_prompt=current_prompt  # 保存当前提示词
)
```

**Step 3: 提交更改**

```bash
git add javisagent/backend/src/routes/claw/conversations.py
git commit -m "feat(backend): save system prompt when creating conversation"
```

---

## Task 5: 修改对话聊天接口

**Files:**
- Modify: `javisagent/backend/src/routes/claw/chat.py`
- Modify: `javisagent/backend/src/services/claw/agent.py`

**Step 1: 修改 agent.py 的 create_agent 函数**

找到 `create_agent` 函数，修改其签名以接受可选的 `custom_system_prompt` 参数：

```python
async def create_agent(
    conversation_id: str,
    working_directory: str,
    llm_model: str = "claude-opus-4-6",
    custom_system_prompt: str = None  # 新增参数
):
    """创建 Claw 智能体"""

    # 使用自定义提示词或默认提示词
    system_prompt_template = custom_system_prompt or SYSTEM_PROMPT_TEMPLATE

    # 格式化提示词
    system_prompt = system_prompt_template.format(working_directory=working_directory)

    # ... 其余代码保持不变
```

**Step 2: 修改 chat.py 的聊天端点**

在聊天端点中，从对话对象读取 `system_prompt` 并传递给 `create_agent`：

```python
# 获取对话
conversation = db.query(ClawConversation).filter(ClawConversation.id == conversation_id).first()
if not conversation:
    raise HTTPException(status_code=404, detail="Conversation not found")

# 创建智能体，传递自定义提示词
agent = await create_agent(
    conversation_id=conversation_id,
    working_directory=conversation.working_directory,
    llm_model=conversation.llm_model,
    custom_system_prompt=conversation.system_prompt  # 传递保存的提示词
)
```

**Step 3: 提交更改**

```bash
git add javisagent/backend/src/services/claw/agent.py javisagent/backend/src/routes/claw/chat.py
git commit -m "feat(backend): use conversation's system prompt in chat"
```

---

## Task 6: 创建前端 API 服务

**Files:**
- Create: `javisagent/frontend/src/services/promptApi.ts`

**Step 1: 创建 API 服务文件**

```typescript
import api from './api';

export interface PromptInfo {
  id: string;
  name: string;
  description: string;
}

export interface PromptDetail {
  id: string;
  name: string;
  content: string;
  default_content: string;
}

export interface PromptUpdateRequest {
  content: string;
}

export interface PromptUpdateResponse {
  success: boolean;
  message: string;
}

export interface PromptResetResponse {
  success: boolean;
  content: string;
}

export const promptApi = {
  // 获取提示词列表
  getPrompts: async (): Promise<{ prompts: PromptInfo[] }> => {
    const response = await api.get('/claw/prompts');
    return response.data;
  },

  // 获取提示词详情
  getPromptDetail: async (id: string): Promise<PromptDetail> => {
    const response = await api.get(`/claw/prompts/${id}`);
    return response.data;
  },

  // 更新提示词
  updatePrompt: async (id: string, content: string): Promise<PromptUpdateResponse> => {
    const response = await api.put(`/claw/prompts/${id}`, { content });
    return response.data;
  },

  // 重置提示词
  resetPrompt: async (id: string): Promise<PromptResetResponse> => {
    const response = await api.post(`/claw/prompts/${id}/reset`);
    return response.data;
  },
};
```

**Step 2: 提交更改**

```bash
git add javisagent/frontend/src/services/promptApi.ts
git commit -m "feat(frontend): add prompt management API service"
```

---

## Task 7: 创建提示词管理页面

**Files:**
- Create: `javisagent/frontend/src/pages/PromptManagementPage.tsx`

**Step 1: 创建页面组件**

```typescript
import React, { useState, useEffect } from 'react';
import { Layout, Menu, Input, Button, message, Space, Typography } from 'antd';
import { promptApi, PromptInfo, PromptDetail } from '../services/promptApi';

const { Sider, Content } = Layout;
const { TextArea } = Input;
const { Title, Text } = Typography;

const PromptManagementPage: React.FC = () => {
  const [prompts, setPrompts] = useState<PromptInfo[]>([]);
  const [selectedPromptId, setSelectedPromptId] = useState<string>('');
  const [promptDetail, setPromptDetail] = useState<PromptDetail | null>(null);
  const [content, setContent] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  // 加载提示词列表
  useEffect(() => {
    loadPrompts();
  }, []);

  // 当选中提示词变化时，加载详情
  useEffect(() => {
    if (selectedPromptId) {
      loadPromptDetail(selectedPromptId);
    }
  }, [selectedPromptId]);

  const loadPrompts = async () => {
    try {
      setLoading(true);
      const data = await promptApi.getPrompts();
      setPrompts(data.prompts);

      // 默认选中第一个
      if (data.prompts.length > 0) {
        setSelectedPromptId(data.prompts[0].id);
      }
    } catch (error) {
      message.error('加载提示词列表失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const loadPromptDetail = async (id: string) => {
    try {
      setLoading(true);
      const detail = await promptApi.getPromptDetail(id);
      setPromptDetail(detail);
      setContent(detail.content);
    } catch (error) {
      message.error('加载提示词详情失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!content.trim()) {
      message.error('提示词不能为空');
      return;
    }

    try {
      setSaving(true);
      await promptApi.updatePrompt(selectedPromptId, content);
      message.success('保存成功，新对话将使用此提示词');

      // 重新加载详情
      await loadPromptDetail(selectedPromptId);
    } catch (error: any) {
      message.error(error.response?.data?.detail || '保存失败');
      console.error(error);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    try {
      setSaving(true);
      const result = await promptApi.resetPrompt(selectedPromptId);
      setContent(result.content);
      message.success('已重置为默认提示词');

      // 重新加载详情
      await loadPromptDetail(selectedPromptId);
    } catch (error: any) {
      message.error(error.response?.data?.detail || '重置失败');
      console.error(error);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Layout style={{ height: '100vh' }}>
      <Sider width={200} theme="light" style={{ borderRight: '1px solid #f0f0f0' }}>
        <div style={{ padding: '16px', borderBottom: '1px solid #f0f0f0' }}>
          <Title level={5} style={{ margin: 0 }}>提示词管理</Title>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedPromptId]}
          items={prompts.map(prompt => ({
            key: prompt.id,
            label: prompt.name,
            onClick: () => setSelectedPromptId(prompt.id),
          }))}
        />
      </Sider>
      <Content style={{ padding: '24px', overflow: 'auto' }}>
        {promptDetail && (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <div>
              <Title level={4}>{promptDetail.name}</Title>
              <Text type="secondary">编辑后保存，新对话将使用此提示词</Text>
            </div>

            <TextArea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={20}
              placeholder="请输入系统提示词"
              style={{ fontFamily: 'monospace' }}
            />

            <Space>
              <Button
                type="primary"
                onClick={handleSave}
                loading={saving}
              >
                保存
              </Button>
              <Button
                onClick={handleReset}
                loading={saving}
              >
                重置为默认
              </Button>
            </Space>
          </Space>
        )}
      </Content>
    </Layout>
  );
};

export default PromptManagementPage;
```

**Step 2: 提交更改**

```bash
git add javisagent/frontend/src/pages/PromptManagementPage.tsx
git commit -m "feat(frontend): add prompt management page"
```

---

## Task 8: 添加路由和菜单

**Files:**
- Modify: `javisagent/frontend/src/App.tsx`
- Modify: `javisagent/frontend/src/components/Layout/SideMenu.tsx`

**Step 1: 在 App.tsx 中添加路由**

导入页面组件：
```typescript
import PromptManagementPage from './pages/PromptManagementPage';
```

在路由配置中添加：
```typescript
<Route path="/claw/prompt-management" element={<PromptManagementPage />} />
```

**Step 2: 在 SideMenu.tsx 中添加菜单项**

找到 Claw 菜单配置，修改为：
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

在 `handleMenuClick` 函数中添加路由映射：
```typescript
const routeMap: Record<string, string> = {
  // ... 其他路由
  'claw-chat': '/claw/chat',
  'prompt-management': '/claw/prompt-management',
};
```

**Step 3: 提交更改**

```bash
git add javisagent/frontend/src/App.tsx javisagent/frontend/src/components/Layout/SideMenu.tsx
git commit -m "feat(frontend): add prompt management route and menu"
```

---

## Task 9: 测试功能

**Step 1: 启动后端服务**

```bash
cd javisagent/backend
conda activate lcv1
python src/main.py
```

**Step 2: 启动前端服务**

```bash
cd javisagent/frontend
npm run dev
```

**Step 3: 测试提示词管理功能**

1. 访问 http://localhost:5173
2. 点击左侧菜单 "Claw" -> "提示词管理"
3. 查看默认系统提示词是否正确显示
4. 编辑提示词内容
5. 点击"保存"按钮，验证保存成功提示
6. 点击"重置为默认"按钮，验证重置成功

**Step 4: 测试新对话使用新提示词**

1. 修改并保存提示词
2. 创建新对话
3. 发送消息，观察智能体行为是否符合新提示词
4. 检查后端日志，确认使用了新提示词

**Step 5: 测试旧对话使用旧提示词**

1. 使用已存在的对话
2. 发送消息，确认仍使用创建时的提示词
3. 验证修改提示词不影响现有对话

---

## Task 10: 最终提交

**Step 1: 运行完整测试**

确保所有功能正常工作：
- 提示词列表加载
- 提示词详情显示
- 提示词编辑和保存
- 提示词重置
- 新对话使用新提示词
- 旧对话不受影响

**Step 2: 创建最终提交**

```bash
git add -A
git commit -m "feat: implement prompt management feature

- Add system_prompt field to ClawConversation model
- Create prompt management API routes
- Implement prompt read/write/reset logic
- Create prompt management page with edit UI
- Add route and menu integration
- Support new conversations using updated prompts
- Maintain backward compatibility for existing conversations"
```

---

## 完成

所有任务已完成。提示词管理功能已成功实现，用户可以通过 Web 界面管理系统提示词，修改后的提示词将在新对话中生效。
