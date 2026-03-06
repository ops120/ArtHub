from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class ImageResult:
    """单张图像结果"""
    b64: Optional[str] = None
    url: Optional[str] = None
    revised_prompt: Optional[str] = None


@dataclass
class GenerationResponse:
    """同步生成响应"""
    success: bool
    data: List[ImageResult] = field(default_factory=list)
    error: Optional[str] = None
    model: Optional[str] = None
    processing_time: Optional[float] = None
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": [
                {
                    "b64": img.b64,
                    "url": img.url,
                    "revised_prompt": img.revised_prompt
                }
                for img in self.data
            ],
            "error": self.error,
            "model": self.model,
            "processing_time": self.processing_time
        }


@dataclass
class AsyncGenerationResponse:
    """异步生成响应"""
    success: bool
    task_id: Optional[str] = None
    status: str = "pending"
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "task_id": self.task_id,
            "status": self.status,
            "error": self.error
        }


@dataclass
class TaskQueryResponse:
    """任务查询响应"""
    success: bool
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: Optional[float] = None
    download_url: Optional[str] = None
    preview_url: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "task_id": self.task_id,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "progress": self.progress,
            "download_url": self.download_url,
            "preview_url": self.preview_url
        }
