import uvicorn
import sys
import os

# 添加当前目录到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
