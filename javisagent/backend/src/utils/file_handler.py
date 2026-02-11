import os
import uuid
from typing import Optional

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads')

# 确保上传目录存在
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

def generate_file_id() -> str:
    """生成唯一的文件 ID"""
    return str(uuid.uuid4())

def save_uploaded_file(file_content: bytes, filename: str) -> str:
    """保存上传的文件并返回文件 ID"""
    file_id = generate_file_id()
    # 保留文件扩展名
    ext = os.path.splitext(filename)[1]
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")
    
    with open(file_path, 'wb') as f:
        f.write(file_content)
    
    return file_id

def get_file_path(file_id: str) -> Optional[str]:
    """根据文件 ID 获取文件路径"""
    for filename in os.listdir(UPLOAD_DIR):
        if filename.startswith(file_id):
            return os.path.join(UPLOAD_DIR, filename)
    return None

def delete_file(file_id: str) -> bool:
    """删除指定的文件"""
    file_path = get_file_path(file_id)
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
        return True
    return False

def get_file_size(file_id: str) -> Optional[int]:
    """获取文件大小（字节）"""
    file_path = get_file_path(file_id)
    if file_path and os.path.exists(file_path):
        return os.path.getsize(file_path)
    return None
