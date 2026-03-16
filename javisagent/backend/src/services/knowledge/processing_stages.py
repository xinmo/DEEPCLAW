"""文档处理阶段定义"""

from enum import Enum
from typing import Dict, Any


class ProcessingStage(str, Enum):
    """处理阶段枚举"""
    UPLOADING = "uploading"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    STORING = "storing"
    COMPLETED = "completed"
    FAILED = "failed"


# 阶段描述信息
STAGE_MESSAGES: Dict[str, str] = {
    ProcessingStage.UPLOADING: "正在上传文件...",
    ProcessingStage.PARSING: "正在解析文档内容...",
    ProcessingStage.CHUNKING: "正在切分文本...",
    ProcessingStage.EMBEDDING: "正在生成向量...",
    ProcessingStage.STORING: "正在存储到知识库...",
    ProcessingStage.COMPLETED: "处理完成",
    ProcessingStage.FAILED: "处理失败",
}

# 阶段进度映射（每个阶段开始时的基础进度）
STAGE_PROGRESS: Dict[str, int] = {
    ProcessingStage.UPLOADING: 0,
    ProcessingStage.PARSING: 10,
    ProcessingStage.CHUNKING: 50,
    ProcessingStage.EMBEDDING: 60,
    ProcessingStage.STORING: 90,
    ProcessingStage.COMPLETED: 100,
    ProcessingStage.FAILED: 0,
}


def get_stage_info(stage: str) -> Dict[str, Any]:
    """获取阶段信息"""
    return {
        "stage": stage,
        "message": STAGE_MESSAGES.get(stage, "处理中..."),
        "progress": STAGE_PROGRESS.get(stage, 0),
    }
