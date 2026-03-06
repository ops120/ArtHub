from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Task:
    """任务数据模型"""
    task_id: str
    task_type: str
    vendor_id: str
    model: str
    status: str = "pending"
    
    prompt: Optional[str] = None
    image_url: Optional[str] = None
    mask_url: Optional[str] = None
    
    size: Optional[str] = None
    duration: Optional[int] = 5
    
    result_url: Optional[str] = None
    result_b64: Optional[str] = None
    
    error_message: Optional[str] = None
    progress: float = 0.0
    
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "vendor_id": self.vendor_id,
            "model": self.model,
            "status": self.status,
            "prompt": self.prompt,
            "image_url": self.image_url,
            "mask_url": self.mask_url,
            "size": self.size,
            "duration": self.duration,
            "result_url": self.result_url,
            "result_b64": self.result_b64,
            "error_message": self.error_message,
            "progress": self.progress,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Task':
        return cls(**data)
    
    def update_status(self, status: str):
        self.status = status
        self.updated_at = datetime.now().isoformat()
        if status in ["completed", "failed"]:
            self.completed_at = datetime.now().isoformat()
    
    def is_finished(self) -> bool:
        return self.status in ["completed", "failed"]
