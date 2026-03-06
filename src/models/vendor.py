from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class VendorConfig:
    """厂商配置数据模型"""
    
    vendor_id: str
    name: str
    base_url: str
    api_key: str
    
    description: str = ""
    enabled: bool = True
    priority: int = 100
    
    support_text2img: bool = False
    support_edit: bool = False
    support_txt2vid: bool = False
    support_img2vid: bool = False
    
    text2img_models: List[str] = field(default_factory=list)
    edit_models: List[str] = field(default_factory=list)
    txt2vid_models: List[str] = field(default_factory=list)
    img2vid_models: List[str] = field(default_factory=list)
    
    timeout: int = 60
    max_retries: int = 3
    custom_headers: Dict[str, str] = field(default_factory=dict)
    
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        return {
            "vendor_id": self.vendor_id,
            "name": self.name,
            "base_url": self.base_url,
            "api_key": self.api_key,
            "description": self.description,
            "enabled": self.enabled,
            "priority": self.priority,
            "support_text2img": self.support_text2img,
            "support_edit": self.support_edit,
            "support_txt2vid": self.support_txt2vid,
            "support_img2vid": self.support_img2vid,
            "text2img_models": self.text2img_models,
            "edit_models": self.edit_models,
            "txt2vid_models": self.txt2vid_models,
            "img2vid_models": self.img2vid_models,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "custom_headers": self.custom_headers,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'VendorConfig':
        return cls(**data)
    
    def get_all_models(self) -> List[str]:
        models = []
        if self.support_text2img:
            models.extend(self.text2img_models)
        if self.support_edit:
            models.extend(self.edit_models)
        if self.support_txt2vid:
            models.extend(self.txt2vid_models)
        if self.support_img2vid:
            models.extend(self.img2vid_models)
        return list(set(models))
    
    def supports_task(self, task_type: str) -> bool:
        if task_type == "text2img":
            return self.support_text2img
        elif task_type == "edit":
            return self.support_edit
        elif task_type == "txt2vid":
            return self.support_txt2vid
        elif task_type == "img2vid":
            return self.support_img2vid
        return False
