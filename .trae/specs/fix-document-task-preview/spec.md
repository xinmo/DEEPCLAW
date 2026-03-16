# 文档解析任务命名与历史任务文件预览修复 Spec

## Why
用户反馈两个问题：
1. 任务名称应该以上传的文档名字命名（当前 URL 解析任务使用 URL 作为名称，不够友好）
2. 点击历史任务时无法查看文件预览，显示"请上传文件以查看预览"

## What Changes
- 后端新增文件下载 API，支持根据 file_id 获取文件内容
- 前端 FilePreview 组件支持通过 file_id 加载文件预览
- 前端加载历史任务时，同时获取 file_id 用于文件预览

## Impact
- Affected code: 
  - `backend/src/routes/document.py` - 新增文件下载接口
  - `frontend/src/components/DocumentParse/FilePreview.tsx` - 支持远程文件预览
  - `frontend/src/pages/DocumentParsePage.tsx` - 传递 file_id 给预览组件
  - `frontend/src/services/api.ts` - 新增文件下载 API

## ADDED Requirements

### Requirement: 文件下载接口
后端系统 SHALL 提供文件下载接口，支持根据 file_id 获取已上传的文件内容。

#### Scenario: 成功下载文件
- **WHEN** 前端请求 `GET /api/document/file/{file_id}`
- **THEN** 返回文件内容，Content-Type 根据文件扩展名自动设置

#### Scenario: 文件不存在
- **WHEN** 前端请求不存在的 file_id
- **THEN** 返回 404 错误

### Requirement: 历史任务文件预览
前端系统 SHALL 支持历史任务的文件预览功能。

#### Scenario: 查看历史任务文件预览
- **WHEN** 用户点击一个已完成的历史任务
- **THEN** 文件预览区域显示该任务对应的文件内容

#### Scenario: URL 解析任务无文件预览
- **WHEN** 用户点击一个 URL 解析任务（无关联文件）
- **THEN** 文件预览区域显示"该任务为 URL 解析，无文件预览"

## MODIFIED Requirements

### Requirement: Task 数据结构
Task 接口 SHALL 包含 file_id 字段，用于关联上传的文件。

**变更内容**：
- 前端 Task 接口已包含 file_id 字段
- 加载历史任务时需要正确映射 file_id
