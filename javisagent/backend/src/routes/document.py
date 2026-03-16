from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Body
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import uuid
import os
from typing import Optional, List

from src.models import get_db, Task, TaskStatus
from src.schemas import UploadResponse, ParseResponse, TaskStatusResponse, Task as TaskSchema, ParseRequest, ExtractProgress
from src.utils.file_handler import save_uploaded_file, get_file_path
from src.services.mineru import mineru_client

router = APIRouter(prefix='/api/document', tags=['document'])

# HTML 相关扩展名
HTML_EXTENSIONS = {'.html', '.htm'}
# 纯文本扩展名（不需要 MinerU 解析）
TEXT_EXTENSIONS = {'.txt', '.md', '.json'}

# 文件扩展名到 MIME 类型的映射
MIME_TYPES = {
    '.pdf': 'application/pdf',
    '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.ppt': 'application/vnd.ms-powerpoint',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    '.xls': 'application/vnd.ms-excel',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.txt': 'text/plain',
    '.md': 'text/markdown',
    '.json': 'application/json',
    '.html': 'text/html',
    '.htm': 'text/html',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
    '.bmp': 'image/bmp',
}

def _is_html_file(filename: str) -> bool:
    ext = os.path.splitext(filename)[1].lower()
    return ext in HTML_EXTENSIONS

def _is_text_file(filename: str) -> bool:
    """判断是否为纯文本文件（不需要 MinerU 解析）"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in TEXT_EXTENSIONS

def _is_html_url(url: str) -> bool:
    """判断 URL 是否应使用 MinerU-HTML 模型"""
    lower = url.lower()
    # 如果 URL 以 .html/.htm 结尾，或者不像文档文件，视为网页
    doc_exts = ('.pdf', '.doc', '.docx', '.ppt', '.pptx', '.png', '.jpg', '.jpeg')
    if any(lower.endswith(ext) for ext in doc_exts):
        return False
    return True

@router.post('/upload', response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """上传文件"""
    try:
        file_content = await file.read()
        if len(file_content) > 200 * 1024 * 1024:
            raise HTTPException(status_code=413, detail='File size exceeds 200MB limit')

        file_id = save_uploaded_file(file_content, file.filename)
        return UploadResponse(file_id=file_id, file_name=file.filename)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'File upload failed: {str(e)}')

@router.post('/parse', response_model=ParseResponse)
async def parse_document(request: ParseRequest, db: Session = Depends(get_db)):
    """解析文档"""
    try:
        task_id = str(uuid.uuid4())

        if request.file_id:
            # 文件上传解析流程：使用 /file-urls/batch
            file_path = get_file_path(request.file_id)
            if not file_path:
                raise HTTPException(status_code=404, detail='File not found')

            # 优先使用传入的原始文件名，否则从路径提取（兼容旧数据）
            filename = request.file_name or os.path.basename(file_path)

            # 纯文本文件直接读取，不需要 MinerU 解析
            if _is_text_file(filename):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    with open(file_path, 'r', encoding='gbk') as f:
                        content = f.read()

                task = Task(
                    id=task_id,
                    name=filename,
                    status=TaskStatus.COMPLETED,
                    file_id=request.file_id,
                    file_name=filename,
                    result=content
                )
                db.add(task)
                db.commit()
                db.refresh(task)
                return ParseResponse(task_id=task_id)

            model_version = 'MinerU-HTML' if _is_html_file(filename) else 'vlm'

            # 1. 申请上传链接
            files = [{'name': filename, 'data_id': request.file_id}]
            upload_response = mineru_client.get_upload_urls(files, model_version=model_version)

            if upload_response.get('code') != 0:
                raise HTTPException(status_code=500, detail=f'MinerU API error: {upload_response.get("msg")}')

            batch_id = upload_response.get('data', {}).get('batch_id')
            upload_urls = upload_response.get('data', {}).get('file_urls', [])
            if not upload_urls or not batch_id:
                raise HTTPException(status_code=500, detail='Failed to get upload URL from MinerU')

            # 2. 上传文件到预签名 URL
            upload_success = mineru_client.upload_file(upload_urls[0], file_path)
            if not upload_success:
                raise HTTPException(status_code=500, detail='Failed to upload file to MinerU')

            # 3. 系统自动提交解析任务，用 batch_id 跟踪
            task = Task(
                id=task_id,
                name=filename,
                status=TaskStatus.RUNNING,
                file_id=request.file_id,
                file_name=filename,
                mineru_batch_id=batch_id
            )
            db.add(task)
            db.commit()
            db.refresh(task)

        elif request.url:
            # URL 解析流程：使用 /extract/task
            model_version = 'MinerU-HTML' if _is_html_url(request.url) else 'vlm'
            parse_response = mineru_client.create_parse_task(request.url, model_version=model_version)

            if parse_response.get('code') != 0:
                raise HTTPException(status_code=500, detail=f'MinerU API error: {parse_response.get("msg")}')

            mineru_task_id = parse_response.get('data', {}).get('task_id')

            task = Task(
                id=task_id,
                name=request.url,
                status=TaskStatus.RUNNING,
                mineru_task_id=mineru_task_id
            )
            db.add(task)
            db.commit()
            db.refresh(task)
        else:
            raise HTTPException(status_code=400, detail='Either file_id or url is required')

        return ParseResponse(task_id=task_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Parse failed: {str(e)}')

@router.get('/task/{task_id}', response_model=TaskStatusResponse)
async def get_task_status(task_id: str, db: Session = Depends(get_db)):
    """获取任务状态"""
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail='Task not found')

        progress = None

        if task.status == TaskStatus.RUNNING:
            try:
                if task.mineru_task_id:
                    # URL 解析：用 task_id 查询
                    status_response = mineru_client.get_task_status(task.mineru_task_id)
                    if status_response.get('code') == 0:
                        data = status_response.get('data', {})
                        progress = _handle_task_result(task, data, db)

                elif task.mineru_batch_id:
                    # 文件上传解析：用 batch_id 查询
                    batch_response = mineru_client.get_batch_status(task.mineru_batch_id)
                    if batch_response.get('code') == 0:
                        results = batch_response.get('data', {}).get('extract_result', [])
                        if results:
                            data = results[0]
                            progress = _handle_task_result(task, data, db)

            except Exception as e:
                print(f'Error getting task status from MinerU: {str(e)}')

        return TaskStatusResponse(task=task, result=task.result, progress=progress)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to get task status: {str(e)}')


def _handle_task_result(task: Task, data: dict, db: Session):
    """处理 MinerU 返回的任务状态数据，更新 task 并返回 progress"""
    from schemas import ExtractProgress

    state = data.get('state')
    progress = None

    if state == 'done':
        task.status = TaskStatus.COMPLETED
        # 下载 ZIP 并提取 Markdown
        zip_url = data.get('full_zip_url')
        if zip_url:
            markdown = mineru_client.download_and_extract_markdown(zip_url)
            if markdown:
                task.result = markdown
        db.commit()
        db.refresh(task)

    elif state == 'failed':
        task.status = TaskStatus.FAILED
        task.result = data.get('err_msg', 'Unknown error')
        db.commit()
        db.refresh(task)

    # 获取解析进度
    extract_progress = data.get('extract_progress', {})
    if extract_progress:
        extracted_pages = extract_progress.get('extracted_pages', 0)
        total_pages = extract_progress.get('total_pages', 0)
        if total_pages > 0:
            progress = ExtractProgress(
                extracted_pages=extracted_pages,
                total_pages=total_pages
            )

    return progress


@router.delete('/task/{task_id}')
async def delete_task(task_id: str, db: Session = Depends(get_db)):
    """删除任务"""
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail='Task not found')
        # 删除关联的本地文件
        if task.file_id:
            from utils.file_handler import delete_file
            delete_file(task.file_id)
        db.delete(task)
        db.commit()
        return {'message': 'Task deleted'}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to delete task: {str(e)}')

@router.get('/tasks', response_model=List[TaskSchema])
async def get_tasks(db: Session = Depends(get_db)):
    """获取任务列表"""
    try:
        tasks = db.query(Task).order_by(Task.created_at.desc()).all()
        return tasks
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to get tasks: {str(e)}')

@router.post('/tasks', response_model=TaskSchema)
async def create_task(db: Session = Depends(get_db)):
    """创建新任务"""
    try:
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            name='新任务',
            status=TaskStatus.PENDING
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to create task: {str(e)}')

@router.get('/file/{file_id}')
async def get_file(file_id: str):
    """
    根据文件 ID 获取文件内容
    用于前端预览历史任务的文件
    """
    file_path = get_file_path(file_id)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail='File not found')
    
    # 获取文件扩展名并设置 Content-Type
    ext = os.path.splitext(file_path)[1].lower()
    media_type = MIME_TYPES.get(ext, 'application/octet-stream')
    
    # 获取文件名
    filename = os.path.basename(file_path)
    
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename
    )
