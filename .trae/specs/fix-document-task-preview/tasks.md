# Tasks

- [x] Task 1: 后端新增文件下载接口
  - [x] SubTask 1.1: 在 document.py 中添加 `GET /api/document/file/{file_id}` 接口
  - [x] SubTask 1.2: 根据文件扩展名设置正确的 Content-Type
  - [x] SubTask 1.3: 处理文件不存在的情况，返回 404 错误

- [x] Task 2: 前端 API 新增文件下载方法
  - [x] SubTask 2.1: 在 api.ts 中添加 `getFile(file_id)` 方法
  - [x] SubTask 2.2: 返回 Blob 对象用于预览

- [x] Task 3: 修改 FilePreview 组件支持远程文件
  - [x] SubTask 3.1: 新增 `fileId` 和 `fileName` props
  - [x] SubTask 3.2: 当 fileId 存在时，调用 API 获取文件内容
  - [x] SubTask 3.3: 支持加载状态显示
  - [x] SubTask 3.4: 处理 URL 解析任务无文件的情况

- [x] Task 4: 修改 DocumentParsePage 传递 file_id
  - [x] SubTask 4.1: 加载历史任务时正确映射 file_id 和 file_name
  - [x] SubTask 4.2: 传递 file_id 和 file_name 给 FilePreview 组件

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 2]
- [Task 4] depends on [Task 3]
