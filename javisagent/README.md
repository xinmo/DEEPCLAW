# JAVISAGENT 工作台

JAVISAGENT 是一个智能解析工作台，支持文档和网页内容的解析，使用 minerU 的开源 API 进行文档解析。

## 功能特性

- **智能解析**：支持 PDF、DOC、DOCX、PPT、PPTX、PNG、JPG 等多种文件格式的解析
- **网页解析**：支持通过 URL 解析网页内容
- **任务管理**：支持创建、查看和管理解析任务
- **实时预览**：上传文件后可查看文件预览
- **Markdown 输出**：解析结果以 Markdown 格式展示，支持图片、表格、代码等元素

## 技术栈

- **前端**：React + TypeScript + Ant Design + Lucide React
- **后端**：Python + FastAPI + SQLAlchemy + SQLite
- **API**：minerU 开源 API

## 快速开始

### 前置条件

- Node.js 16+
- Python 3.8+
- pip
- npm

### 安装步骤

1. **克隆项目**

2. **安装前端依赖**
   ```bash
   cd frontend
   npm install
   ```

3. **安装后端依赖**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. **配置环境变量**
   - 复制 `.env.example` 文件为 `.env`
   - 填写 `MINERU_API_TOKEN`（从 minerU 官网申请）

5. **启动后端服务**
   ```bash
   cd backend
   python src/main.py
   ```

6. **启动前端服务**
   ```bash
   cd frontend
   npm run dev
   ```

7. **访问应用**
   打开浏览器访问 `http://localhost:5173`

## 项目结构

```
javisagent/
├── frontend/           # 前端代码
│   ├── src/
│   │   ├── components/ # 组件
│   │   ├── pages/      # 页面
│   │   ├── services/   # API 服务
│   │   ├── styles/     # 样式
│   │   └── utils/      # 工具函数
│   └── package.json
├── backend/            # 后端代码
│   ├── src/
│   │   ├── routes/     # 路由
│   │   ├── services/   # 服务
│   │   ├── models/     # 数据模型
│   │   ├── schemas/    # 数据传输对象
│   │   └── utils/      # 工具函数
│   └── requirements.txt
├── .env.example        # 环境变量模板
└── README.md           # 项目说明
```

## API 文档

启动后端服务后，可访问 `http://localhost:8000/docs` 查看自动生成的 API 文档。

## 注意事项

- 文件大小限制：单个文件不超过 200MB
- 解析时间：根据文件大小和复杂度，解析时间可能会有所不同
- API Token：需要从 minerU 官网申请 API Token 才能使用解析功能

## 许可证

MIT
