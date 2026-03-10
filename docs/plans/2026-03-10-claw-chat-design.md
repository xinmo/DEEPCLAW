# Claw - 对话龙虾功能设计文档

**日期：** 2026-03-10
**版本：** 1.0
**状态：** 已批准

## 1. 概述

### 1.1 功能描述

Claw（对话龙虾）是 JAVISAGENT 的新增功能模块，为用户提供与 Deep Agents 进行对话的编程助手界面。用户可以通过自然语言与 AI 智能体交互，完成代码编写、文件操作、命令执行等编程任务。

### 1.2 核心特性

- **多对话管理** - 支持创建、切换、重命名、删除多个独立对话会话
- **自定义工作目录** - 用户可配置工作目录，Agent 可访问本地任意文件
- **完整工具支持** - 启用所有 Deep Agent 工具（文件系统、Shell 命令、规划、子智能体）
- **CLI 风格展示** - 统一的聊天流界面，实时展示所有执行过程
- **并行子智能体** - 支持多个子智能体并行执行，实时显示进度
- **流式响应** - 使用 SSE 技术实现流式输出，提供即时反馈

### 1.3 设计目标

- 提供类似 Claude Code 的编程助手体验
- 与现有功能模块保持一致的用户体验
- 快速开发上线（预计 3-5 天完成核心功能）
- 易于扩展和维护

---

## 2. 架构设计

### 2.1 技术栈

**前端：**
- React 18 + TypeScript
- Ant Design 5.x
- SSE (Server-Sent Events)
- 复用 KnowledgeChatPage 的布局结构

**后端：**
- FastAPI
- Deep Agents SDK (`deepagents` Python 包)
- SQLAlchemy ORM
- PostgreSQL / SQLite

**集成方式：**
- FastAPI 后端直接集成 Deep Agents SDK
- 通过 `create_deep_agent()` 创建 Agent 实例
- 启用所有工具：文件系统、shell、规划、子智能体

### 2.2 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        前端 (React)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ 对话列表     │  │ 聊天界面     │  │ 配置面板     │     │
│  │ - 搜索       │  │ - 消息展示   │  │ - 工作目录   │     │
│  │ - 新建       │  │ - 工具卡片   │  │ - 模型选择   │     │
│  │ - 删除       │  │ - 子智能体   │  │              │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │ SSE
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    后端 (FastAPI)                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Claw API Routes                          │  │
│  │  /api/claw/conversations  (CRUD)                     │  │
│  │  /api/claw/conversations/{id}/chat  (SSE Stream)     │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Deep Agents Service                         │  │
│  │  - create_deep_agent()                               │  │
│  │  - 文件系统工具                                       │  │
│  │  - Shell 命令执行                                     │  │
│  │  - 规划工具                                           │  │
│  │  - 子智能体管理                                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              数据库 (SQLAlchemy)                      │  │
│  │  - ClawConversation                                  │  │
│  │  - ClawMessage                                       │  │
│  │  - ClawToolCall                                      │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 数据模型

#### ClawConversation（对话会话）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| title | String | 对话标题 |
| working_directory | String | 工作目录路径 |
| llm_model | String | 使用的模型（如 claude-opus-4-6） |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

#### ClawMessage（消息记录）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| conversation_id | UUID | 外键，关联对话 |
| role | Enum | 角色：user / assistant |
| content | Text | 消息内容 |
| metadata | JSON | 元数据（工具调用、子智能体等） |
| created_at | DateTime | 创建时间 |

#### ClawToolCall（工具调用记录）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| message_id | UUID | 外键，关联消息 |
| tool_name | String | 工具名称 |
| tool_input | JSON | 输入参数 |
| tool_output | JSON | 输出结果 |
| status | Enum | 状态：running / success / failed |
| duration | Float | 执行时长（秒） |
| created_at | DateTime | 创建时间 |

### 2.4 API 端点设计

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/claw/conversations` | 创建新对话 |
| GET | `/api/claw/conversations` | 获取对话列表 |
| GET | `/api/claw/conversations/{id}` | 获取对话详情 |
| PUT | `/api/claw/conversations/{id}` | 更新对话（标题、工作目录） |
| DELETE | `/api/claw/conversations/{id}` | 删除对话 |
| GET | `/api/claw/conversations/{id}/messages` | 获取消息历史 |
| POST | `/api/claw/conversations/{id}/chat` | 发送消息（SSE 流式） |
| GET | `/api/claw/models` | 获取可用模型列表 |
| POST | `/api/claw/validate-directory` | 验证工作目录 |

---

## 3. 前端界面设计

### 3.1 页面布局

```
┌─────────────────────────────────────────────────────────────┐
│  [对话历史]          │  Claw - 对话龙虾                      │
│  ├─ 项目A重构        │  ┌─────────────────────────────────┐ │
│  ├─ Bug修复          │  │ 工作目录: /path/to/project  [📁]│ │
│  └─ 新功能开发       │  │ 模型: Claude Opus 4.6       [⚙️]│ │
│                      │  └─────────────────────────────────┘ │
│  [+ 新建对话]        │                                       │
│                      │  ┌─────────────────────────────────┐ │
│  ┌─ 📁 工作目录 ───┐ │  │  聊天区域（CLI 风格）            │ │
│  │ ▼ project/      │ │  │                                   │ │
│  │   ▼ src/        │ │  │  👤 User: 帮我重构这个函数        │ │
│  │     ├─ app.py   │ │  │                                   │ │
│  │     └─ utils.py │ │  │  🤖 Assistant:                    │ │
│  │   └─ tests/     │ │  │  好的，让我先看看这个文件          │ │
│  └─────────────────┘ │  │                                   │ │
│                      │  │  ┌─ 🔧 Tool: read_file ─────┐   │ │
│                      │  │  │ 📄 src/utils/helper.py    │   │ │
│                      │  │  │ ✓ 读取成功 (245 lines)    │   │ │
│                      │  │  └───────────────────────────┘   │ │
│                      │  │                                   │ │
│                      │  │  ┌─ 📝 Planning ─────────────┐   │ │
│                      │  │  │ ☐ 提取重复逻辑            │   │ │
│                      │  │  │ ☐ 添加类型注解            │   │ │
│                      │  │  └───────────────────────────┘   │ │
│                      │  └─────────────────────────────────┘ │
│                      │                                       │
│                      │  ┌─────────────────────────────────┐ │
│                      │  │ 💬 输入消息...      [发送 ➤]    │ │
│                      │  └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 核心组件

**ClawChatPage** - 主页面组件
- 管理对话列表、当前对话、消息流
- 处理 SSE 连接和事件
- 协调各子组件

**ConversationList** - 对话列表组件
- 显示所有对话
- 支持搜索、新建、删除、重命名
- 高亮当前选中对话

**FileTree** - 文件树组件（可折叠）
- 显示工作目录的文件结构
- 点击文件可插入路径到输入框

**ChatArea** - 聊天区域组件
- 渲染用户和 Assistant 消息
- 嵌入各种卡片组件
- 自动滚动到底部

**ToolCallCard** - 工具调用卡片
- 显示工具名称、输入、输出
- 状态指示：运行中 / 成功 / 失败
- 可展开查看详细信息

**ShellCommandCard** - Shell 命令卡片
- 显示命令和执行结果
- 支持展开查看完整输出
- 显示执行时长

**SubAgentCard** - 子智能体卡片
- 显示子智能体名称和任务
- 实时进度条
- 可展开查看详细结果

**SubAgentPoolCard** - 并行子智能体池
- 同时显示多个子智能体
- 网格布局展示
- 统一的进度管理

**PlanningCard** - 规划任务卡片
- 显示任务列表
- 任务状态：待办 / 进行中 / 完成
- 实时更新任务状态

### 3.3 TypeScript 类型定义

```typescript
interface ClawConversation {
  id: string;
  title: string;
  working_directory: string;
  llm_model: string;
  created_at: string;
  updated_at: string;
}

interface ClawMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  toolCalls?: ToolCall[];
  subAgents?: SubAgent[];
  planningTasks?: Task[];
  isStreaming?: boolean;
  timestamp: Date;
}

interface ToolCall {
  id: string;
  toolName: string;
  status: 'running' | 'success' | 'failed';
  input: any;
  output?: any;
  duration?: number;
  error?: string;
}

interface SubAgent {
  id: string;
  name: string;
  task: string;
  status: 'running' | 'success' | 'failed';
  progress?: number;
  result?: any;
  duration?: number;
}

interface Task {
  id: string;
  content: string;
  status: 'pending' | 'in_progress' | 'completed';
}
```

### 3.4 样式设计

**配色方案：**
- 工具调用：蓝色系 `#1890ff`
- Shell 命令：绿色系 `#52c41a`
- 子智能体：紫色系 `#722ed1`
- 规划任务：橙色系 `#fa8c16`
- 错误状态：红色系 `#ff4d4f`

**卡片样式：**
- 圆角：8px
- 阴影：`0 2px 8px rgba(0,0,0,0.08)`
- 边框：1px solid 对应颜色的浅色版本
- 内边距：12px 16px
- 可折叠/展开动画（300ms ease-in-out）

---

## 4. 后端实现设计

### 4.1 Deep Agents 集成

**Agent 创建：**

```python
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver

def create_claw_agent(
    working_directory: str,
    llm_model: str = "claude-opus-4-6"
):
    system_prompt = """
    你是一个专业的编程助手，可以帮助用户完成各种编程任务。

    你可以使用以下工具：
    - 文件系统工具：读取、写入、编辑、搜索文件
    - Shell 命令：执行任何命令行操作
    - 规划工具：分解复杂任务为可执行步骤
    - 子智能体：创建专门的子任务智能体

    工作目录：{working_directory}

    请始终：
    1. 在执行操作前说明你的计划
    2. 使用工具时提供清晰的描述
    3. 遇到错误时提供解决方案
    4. 完成任务后总结结果
    """

    agent = create_deep_agent(
        model=llm_model,
        system_prompt=system_prompt.format(
            working_directory=working_directory
        ),
        checkpointer=MemorySaver(),
        enable_filesystem=True,
        enable_shell=True,
        enable_planning=True,
        enable_subagents=True,
        working_directory=working_directory,
    )

    return agent
```

### 4.2 SSE 事件类型

**前端接收的事件类型：**

| 事件类型 | 说明 | 数据结构 |
|---------|------|---------|
| `text` | 文本内容 | `{type: 'text', content: string}` |
| `tool_call` | 工具调用开始 | `{type: 'tool_call', tool_name, tool_input, status: 'running'}` |
| `tool_result` | 工具调用结果 | `{type: 'tool_result', tool_name, output, status, error?, duration}` |
| `subagent_start` | 子智能体启动 | `{type: 'subagent_start', agent_id, agent_name, task}` |
| `subagent_progress` | 子智能体进度 | `{type: 'subagent_progress', agent_id, progress}` |
| `subagent_complete` | 子智能体完成 | `{type: 'subagent_complete', agent_id, result, duration}` |
| `planning` | 规划任务 | `{type: 'planning', tasks: Task[]}` |
| `done` | 响应完成 | `{type: 'done'}` |
| `error` | 错误 | `{type: 'error', message: string}` |

### 4.3 安全控制

**文件访问：**
- 用户配置工作目录后，Agent 可访问该目录及其子目录
- 不限制访问范围（根据用户需求）
- 记录所有文件操作日志到数据库

**Shell 命令：**
- 允许执行所有命令（根据用户需求）
- 记录命令执行历史
- 捕获标准输出和错误输出
- 设置命令超时（默认 300 秒）

**错误处理：**
- 捕获所有异常并返回友好的错误信息
- 工具调用失败不中断整个对话
- 提供重试机制

---

## 5. 用户交互流程

### 5.1 首次使用流程

```
1. 用户点击 "Claw" → "对话龙虾"
   ↓
2. 显示空状态引导页
   - 提示：选择工作目录开始对话
   - 工作目录选择器（文件夹图标）
   - 模型选择（默认 Claude Opus 4.6）
   - [开始对话] 按钮
   ↓
3. 点击 [开始对话]
   - 验证工作目录
   - 创建新对话
   - 进入聊天界面
```

### 5.2 日常使用流程

```
1. 进入页面
   - 自动加载上次对话（从 localStorage 恢复）
   - 显示对话历史
   ↓
2. 用户输入消息并发送
   - 前端验证输入非空
   - 建立 SSE 连接
   ↓
3. 接收流式响应
   - 实时显示 Agent 思考过程
   - 展示工具调用卡片
   - 显示子智能体进度
   - 更新规划任务状态
   ↓
4. 响应完成
   - 显示最终结果
   - 保存消息到数据库
   - 用户可继续对话
```

### 5.3 多对话管理

```
1. 点击 [+ 新建对话]
   ↓
2. 弹出配置对话框
   - 对话标题（可选，默认"新对话"）
   - 工作目录（必填）
   - 模型选择（默认 Claude Opus 4.6）
   ↓
3. 点击 [创建]
   - 验证工作目录
   - 创建对话记录
   - 切换到新对话
```

**对话操作：**
- 双击标题可编辑
- 右键菜单：重命名、删除
- 搜索框过滤对话

### 5.4 并行子智能体交互

**场景：代码审查 + 测试生成 + 文档更新**

```
1. 用户发送请求："帮我完善这个模块，包括代码审查、测试和文档"
   ↓
2. Agent 启动 3 个子智能体
   - 显示 SubAgentPoolCard
   - 3 个子智能体卡片并排显示
   ↓
3. 实时更新进度
   - 每个子智能体独立显示进度条
   - 显示运行时间
   - 状态图标：⏳ 运行中 / ✓ 完成 / ❌ 失败
   ↓
4. 子智能体完成
   - 卡片状态更新为 ✓ 完成
   - 显示执行时长
   - 可展开查看详细结果
   ↓
5. 全部完成
   - 显示总耗时
   - 汇总所有结果
   - 提供后续操作选项
```

---

## 6. 错误处理与优化

### 6.1 错误处理策略

**工作目录验证：**
- 前端验证：检查路径格式
- 后端验证：检查目录是否存在、是否可访问
- 错误提示：显示具体原因（不存在、无权限等）

**工具调用失败：**
- 在工具卡片中显示错误信息
- 提供 [重试] 按钮
- Agent 自动尝试替代方案

**子智能体失败：**
- 显示失败状态和错误原因
- 不影响其他并行子智能体
- 提供 [重新运行] 选项

**网络中断：**
- SSE 连接断开时自动重连（最多 3 次）
- 保存已接收的部分消息
- 显示连接状态提示

### 6.2 性能优化

**前端优化：**
- 虚拟滚动（消息列表超过 100 条时）
- 工具调用卡片懒加载（默认折叠）
- 防抖输入验证（500ms）
- 图片/大文件预览懒加载

**后端优化：**
- Agent 实例缓存（避免重复创建）
- 异步执行工具调用
- 数据库连接池管理
- 限制单次响应的最大长度（10MB）

**流式响应优化：**
- 批量发送小块数据（减少网络开销）
- 压缩大型工具输出（gzip）
- 设置合理的超时时间

### 6.3 数据持久化

**对话历史：**
- 所有消息存储在数据库
- 工具调用记录单独存储
- 支持导出对话历史（JSON/Markdown）

**工作目录配置：**
- 记住每个对话的工作目录
- 支持快速切换常用目录
- 提供目录历史记录（最近 10 个）

---

## 7. 实施计划

### 7.1 开发阶段

**阶段 1：基础架构（1 天）**
- 创建数据库模型
- 实现基础 API 端点
- 集成 Deep Agents SDK

**阶段 2：前端界面（2 天）**
- 实现页面布局
- 开发核心组件
- 实现 SSE 连接

**阶段 3：功能完善（1 天）**
- 实现工具调用展示
- 实现子智能体展示
- 添加错误处理

**阶段 4：测试优化（1 天）**
- 功能测试
- 性能优化
- Bug 修复

### 7.2 技术风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Deep Agents SDK 兼容性问题 | 高 | 提前测试 SDK，准备降级方案 |
| SSE 连接稳定性 | 中 | 实现自动重连机制 |
| 大文件处理性能 | 中 | 限制文件大小，使用流式处理 |
| 并发子智能体资源消耗 | 低 | 限制最大并发数 |

### 7.3 后续扩展

**短期（1-2 周）：**
- 添加代码高亮显示
- 支持文件差异对比
- 添加快捷命令（如 `/help`, `/clear`）

**中期（1-2 月）：**
- 集成知识库（Agent 可查询知识库）
- 添加代码片段库
- 支持多人协作

**长期（3-6 月）：**
- 支持自定义 Agent 配置
- 添加 Agent 市场（预设 Agent）
- 集成 CI/CD 流程

---

## 8. 总结

Claw（对话龙虾）功能通过集成 Deep Agents SDK，为 JAVISAGENT 提供了强大的编程助手能力。设计采用 CLI 风格的统一聊天流界面，清晰展示所有执行过程，支持多对话管理、自定义工作目录、完整的工具支持和并行子智能体。

**关键优势：**
- 复用现有架构，开发效率高
- 用户体验一致，学习成本低
- 功能强大，支持复杂编程任务
- 易于扩展，可持续迭代

**预期效果：**
- 提升用户编程效率
- 降低重复性工作
- 提供智能化的代码辅助
- 增强 JAVISAGENT 的竞争力
