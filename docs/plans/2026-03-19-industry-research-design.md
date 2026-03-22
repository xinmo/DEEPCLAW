# AI 产业研究室 — 设计文档

**日期**：2026-03-19
**状态**：已批准，待实现
**方案**：方案 A — 单页多视图 + SSE 流式研究

---

## 一、功能概述

在现有 JAVISAGENT 中新增「产业研究室」模块，提供四个核心功能视图：

1. **研究台首页** — 搜索入口 + 历史研究卡片
2. **多智能体研究看板** — 实时展示 AI 研究进度与图谱生长
3. **产业链图谱主界面** — 全屏可交互的分层图谱
4. **环节深度研究** — 数据看板与 AI 报告左右联动

---

## 二、整体架构

### 2.1 页面集成

- 在 `App.tsx` 新增 `industry-research` 路由
- `SideMenu.tsx` 新增「产业研究室」入口，图标使用 `FlaskConical`（lucide-react）
- 与现有页面（ClawChatPage、KnowledgeBasePage 等）平级，无需引入 React Router

### 2.2 前端文件结构

```
src/
├── pages/
│   └── IndustryResearchPage.tsx          # 主页面，状态机控制四个视图
├── components/
│   └── IndustryResearch/
│       ├── ResearchHome.tsx               # 模块一：首页
│       ├── ResearchDashboard.tsx          # 模块二：多智能体看板
│       ├── IndustryGraph.tsx              # 模块三：产业链图谱（@antv/g6）
│       ├── NodeDrawer.tsx                 # 图谱节点右侧抽屉
│       ├── DeepResearch.tsx               # 模块四：深度研究左右联动
│       └── AgentLogPanel.tsx              # 智能体实时日志面板
├── services/
│   └── industryResearchApi.ts            # SSE + REST API 调用
└── types/
    └── industryResearch.ts               # 类型定义
```

### 2.3 后端文件结构

```
src/
├── routes/
│   └── industry_research/
│       ├── __init__.py
│       ├── research.py                   # POST /api/industry-research/start
│       └── stream.py                     # GET /api/industry-research/{id}/stream (SSE)
├── services/
│   └── industry_research/
│       ├── agent_team.py                 # 多智能体团队（基于 deepagents，与 Claw 解耦）
│       ├── graph_builder.py              # 产业链图谱数据构建
│       └── deep_researcher.py            # 深度研究报告生成
└── models/
    └── industry_research.py              # 数据库模型（SQLAlchemy）
```

### 2.4 视图状态机

```
home
  └─(发起研究)→ dashboard（研究进行中，SSE 流式接收）
                  └─(研究完成)→ graph（图谱主界面）
                                  └─(点击深度研究)→ deepResearch
                                                      └─(返回)→ graph
graph → (返回) → home
```

---

## 三、数据流与 API 设计

### 3.1 REST API

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/industry-research/start` | 发起研究，返回 `researchId` |
| `GET` | `/api/industry-research/{id}/stream` | SSE 流式推送进度与图谱数据 |
| `GET` | `/api/industry-research/{id}/graph` | 获取完整图谱数据 |
| `POST` | `/api/industry-research/{id}/deep` | 对某环节启动深度研究，返回新 SSE 流 |
| `GET` | `/api/industry-research/history` | 获取历史研究列表 |

### 3.2 请求体

```typescript
// POST /start
{ query: string, depth: "quick" | "standard" | "deep" }

// POST /deep
{ nodeId: string, nodeName: string }
```

### 3.3 SSE 事件流格式

```typescript
// 智能体状态更新
{ type: "agent_status", data: { agentId, name, status: "running"|"waiting"|"done", action, detail } }

// 实时日志
{ type: "log", data: { timestamp, message } }

// 图谱节点生长
{ type: "graph_node", data: { id, label, layer, status: "done"|"in_progress"|"pending", companies: [], nationalizationRate: number, competitionType: "domestic"|"foreign"|"balanced" } }

// 图谱边
{ type: "graph_edge", data: { source, target } }

// 研究进度
{ type: "progress", data: { percent: number, stage: string } }

// 深度研究报告片段（流式 Markdown）
{ type: "report_chunk", data: { chunk: string } }

// 完成
{ type: "done", data: { researchId: string } }
```

### 3.4 前端顶层状态

```typescript
interface ResearchState {
  view: "home" | "dashboard" | "graph" | "deep";
  researchId: string | null;
  query: string;
  depth: "quick" | "standard" | "deep";
  agents: AgentStatus[];
  logs: LogEntry[];
  graphNodes: GraphNode[];
  graphEdges: GraphEdge[];
  progress: number;
  selectedNodeId: string | null;   // 控制节点抽屉
  deepReport: string;              // 流式拼接 Markdown
  history: ResearchHistory[];
}
```

### 3.5 多智能体团队（后端 deepagents）

四个智能体角色，顺序执行，部分并行：

1. **产业分析师** — 识别产业链层次结构（web_search）
2. **供应链研究员** — 爬取各环节头部企业（agent_browser + web_search）
3. **数据核查员** — 验证企业归属与市场份额
4. **报告撰写员** — 生成环节摘要与投资逻辑

每个智能体通过 SSE `agent_status` 事件实时推送状态变化，日志通过 `log` 事件推送。

---

## 四、核心 UI 组件设计

### 4.1 模块一：ResearchHome

- 顶部搜索区占屏幕 40% 高度，深色渐变背景 `linear-gradient(135deg, #0d1117 0%, #161b22 50%, #1a2332 100%)`
- 搜索框宽度 600px，居中，`Input.Search`，回车或点击触发研究
- 研究深度：`Radio.Group` 按钮样式，三档（快速概览 / 标准研究 / 深度研究）
- 研究深度说明：hover 显示 `Tooltip`，说明预计时长与输出内容
- 热门标签：`Tag` 组件行，点击自动填入搜索框
- 下方历史卡片：`Card` 网格 3 列
  - 进行中：显示进度条 `Progress`
  - 已完成：显示「查看图谱」「更新」按钮

### 4.2 模块二：ResearchDashboard

**布局**：左 30% + 右 70%，`display: flex`

**左栏 — 智能体工作台**：
- 每个智能体卡片：状态图标（`Spin` 运行中 / `CheckCircle` 完成 / `ClockCircle` 等待）+ 名称 + 当前动作文字
- 实时日志：固定高度 `200px` 滚动区，新日志自动 `scrollTop = scrollHeight`

**右栏 — 图谱实时生长**：
- `@antv/g6` Dagre 分层布局，纵向从上到下
- 节点状态动画：
  - 已完成：实色填充
  - 进行中：CSS `@keyframes pulse` 蓝色边框呼吸动画（1.5s 循环）
  - 未到达：虚线边框 + `opacity: 0.4`
- 节点随 SSE `graph_node` 事件动态添加，有淡入动画

### 4.3 模块三：IndustryGraph

**顶部工具栏**（固定）：
- 面包屑（研究主题名）+ 更新时间 + 环节数 + 企业数
- 右侧：缩放 +/- + 全屏 + 标注 + 导出▾ + 分享 + 「深度研究此图谱」按钮
- 色彩图例：🟢国产机遇 🟠外资垄断 🔵均衡竞争

**图谱主体**：
- `@antv/g6` Dagre 布局，`rankdir: "TB"`（从上到下）
- 自定义节点渲染（G6 Custom Node）：
  - 环节名称（大字）
  - 层级标签（小字，如「上游原材料」）
  - 国产化率进度条
  - 企业数量标签
  - 颜色：🟢`#52c41a` 国产机遇 / 🟠`#fa8c16` 外资垄断 / 🔵`#1677ff` 均衡竞争
- 点击节点 → 右侧 `Drawer` 滑出（width=480px），主内容区 `paddingRight: 480px` 避免遮挡

**NodeDrawer 内容**：
- 环节名 + 层级标签
- 环节概述文字
- 核心企业卡片（名称 + 国别 + 市场份额）
- 上游依赖标签
- 最新动态列表
- 「对此环节启动深度研究」CTA 卡片

### 4.4 模块四：DeepResearch

**布局**：左 45% 数据看板 + 右 55% AI 报告，`display: flex`，高度 `calc(100vh - 64px)`

**左栏 — 数据看板**：
- `Tabs` 四个标签页：
  - **市场格局**：横向条形图（纯 CSS 进度条实现）+ 可排序 `Table`（营收/毛利率/PE/国产化率贡献）
  - **原材料价格**：折线趋势图（@antv/g6 或简单 SVG），AI 实时分析文字
  - **竞争壁垒**：雷达图（六维度评分）
  - **投资风险**：风险矩阵卡片列表，🔴高风险 / 🟡中风险 / 🟢低风险
- 企业卡片点击 → 右侧报告 `scrollIntoView` 到对应章节

**右栏 — AI 研究报告**：
- `ReactMarkdown` 渲染，流式 Markdown 打字机效果（`report_chunk` 事件逐步拼接）
- 章节锚点：每个 `##` 标题生成 `id`，供左侧联动滚动
- 固定顶部：报告标题 + 生成进度条

---

## 五、关键技术决策

| 决策点 | 选择 | 原因 |
|--------|------|------|
| 图谱库 | @antv/g6（已有依赖） | 无需新增依赖，KnowledgeGraph 有参考 |
| 实时通信 | SSE（EventSource） | 单向推送，比 WebSocket 更简单，复用现有 ClawChat SSE 模式 |
| 状态管理 | React useState + useReducer | 无需引入外部状态库，与现有项目一致 |
| 报告渲染 | ReactMarkdown（已有依赖） | 已在 ClawChatPage 使用 |
| 后端智能体 | deepagents（独立，与 Claw 解耦） | 复用 deepagents 架构但路由/服务完全独立 |
| 布局 | Ant Design Layout + 自定义 CSS | 与现有项目一致 |

---

## 六、不在本次范围内

- 用户权限控制（研究共享/私有）
- 研究报告 PDF 导出（导出按钮预留，功能后续迭代）
- 移动端适配（桌面端优先）
- 个股研究（查询解析后端，UI 与产业链研究共用）
