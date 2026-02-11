import requests
import os
import zipfile
import io
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

MINERU_API_TOKEN = os.getenv('MINERU_API_TOKEN', '')
MINERU_API_BASE_URL = 'https://mineru.net/api/v4'

class MinerUClient:
    def __init__(self, api_token: str = MINERU_API_TOKEN):
        self.api_token = api_token
        self.base_url = MINERU_API_BASE_URL
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_token}'
        }

    def get_upload_urls(self, files: list, model_version: str = 'vlm') -> Dict[str, Any]:
        """申请文件上传链接 (POST /file-urls/batch)"""
        url = f'{self.base_url}/file-urls/batch'
        data = {
            'files': files,
            'model_version': model_version
        }
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

    def upload_file(self, upload_url: str, file_path: str) -> bool:
        """上传文件到预签名 URL (PUT)，不设置 Content-Type"""
        with open(file_path, 'rb') as f:
            response = requests.put(upload_url, data=f)
        return response.status_code == 200

    def create_parse_task(self, url: str, model_version: str = 'vlm') -> Dict[str, Any]:
        """创建 URL 解析任务 (POST /extract/task)"""
        api_url = f'{self.base_url}/extract/task'
        data = {
            'url': url,
            'model_version': model_version
        }
        response = requests.post(api_url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """查询单个任务状态 (GET /extract/task/{task_id})"""
        url = f'{self.base_url}/extract/task/{task_id}'
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """查询批量任务状态 (GET /extract-results/batch/{batch_id})"""
        url = f'{self.base_url}/extract-results/batch/{batch_id}'
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def download_and_extract_markdown(self, zip_url: str) -> Optional[str]:
        """下载 full_zip_url 并从 ZIP 中提取 Markdown 内容"""
        try:
            response = requests.get(zip_url, stream=True)
            if response.status_code != 200:
                return None
            zip_data = io.BytesIO(response.content)
            with zipfile.ZipFile(zip_data, 'r') as zf:
                # 查找 .md 文件
                md_files = [f for f in zf.namelist() if f.endswith('.md')]
                if md_files:
                    return zf.read(md_files[0]).decode('utf-8')
            return None
        except Exception as e:
            print(f'Error downloading/extracting markdown: {e}')
            return None

# 创建全局实例
mineru_client = MinerUClient()
