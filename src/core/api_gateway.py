from typing import Dict, Any, Optional
from src.core.vendor_manager import VendorManager
from src.adapters.base_adapter import BaseAdapter
from src.models.response import GenerationResponse, AsyncGenerationResponse, TaskQueryResponse
import logging

logger = logging.getLogger(__name__)


class TaskType:
    TEXT2IMG = "text2img"
    IMAGE_EDIT = "edit"
    TEXT2VIDEO = "txt2vid"
    IMAGE2VIDEO = "img2vid"


class APIGateway:
    """统一 API 网关 - 对外提供统一接口"""
    
    def __init__(self, vendor_manager: VendorManager):
        self.vendor_manager = vendor_manager
        self._adapter_cache: Dict[str, BaseAdapter] = {}
    
    def generate(
        self,
        vendor_id: str,
        task_type: str,
        prompt: str,
        model: str = None,
        **kwargs
    ) -> GenerationResponse:
        vendor = self.vendor_manager.get_vendor(vendor_id)
        if not vendor:
            return GenerationResponse(
                success=False,
                error=f"厂商不存在: {vendor_id}"
            )
        
        if not vendor.enabled:
            return GenerationResponse(
                success=False,
                error=f"厂商已禁用: {vendor.name}"
            )
        
        adapter = self._get_adapter(vendor)
        
        try:
            if task_type == TaskType.TEXT2IMG:
                return adapter.generate_image(prompt, model, **kwargs)
            elif task_type == TaskType.IMAGE_EDIT:
                return adapter.edit_image(
                    image=kwargs.get("image"),
                    prompt=prompt,
                    model=model,
                    mask=kwargs.get("mask")
                )
            else:
                return GenerationResponse(
                    success=False,
                    error=f"该任务类型不支持同步生成: {task_type}"
                )
        except Exception as e:
            logger.error(f"生成失败: {e}")
            return GenerationResponse(success=False, error=str(e))
    
    def generate_async(
        self,
        vendor_id: str,
        task_type: str,
        prompt: str,
        model: str = None,
        **kwargs
    ) -> AsyncGenerationResponse:
        vendor = self.vendor_manager.get_vendor(vendor_id)
        if not vendor:
            return AsyncGenerationResponse(
                success=False,
                error=f"厂商不存在: {vendor_id}"
            )
        
        if not vendor.enabled:
            return AsyncGenerationResponse(
                success=False,
                error=f"厂商已禁用: {vendor.name}"
            )
        
        adapter = self._get_adapter(vendor)
        
        try:
            if task_type == TaskType.TEXT2VIDEO:
                return adapter.generate_video(prompt, model, **kwargs)
            elif task_type == TaskType.IMAGE2VIDEO:
                return adapter.image_to_video(
                    image=kwargs.get("image"),
                    prompt=prompt,
                    model=model,
                    **kwargs
                )
            elif task_type == TaskType.TEXT2IMG:
                return adapter.generate_image_async(
                    prompt=prompt,
                    model=model,
                    negative_prompt=kwargs.get("negative_prompt", ""),
                    size=kwargs.get("size", "1024x1024"),
                    n=kwargs.get("n", 1)
                )
            elif task_type == TaskType.IMAGE_EDIT:
                return adapter.edit_image_async(
                    prompt=prompt,
                    image=kwargs.get("image"),
                    model=model,
                    mask=kwargs.get("mask"),
                    size=kwargs.get("size", "1024x1024")
                )
            else:
                return AsyncGenerationResponse(
                    success=False,
                    error=f"该任务类型不支持异步: {task_type}"
                )
        except Exception as e:
            logger.error(f"异步生成失败: {e}")
            return AsyncGenerationResponse(success=False, error=str(e))
    
    def query_task(
        self,
        vendor_id: str,
        task_id: str
    ) -> TaskQueryResponse:
        vendor = self.vendor_manager.get_vendor(vendor_id)
        if not vendor:
            return TaskQueryResponse(
                success=False,
                task_id=task_id,
                status="failed",
                error=f"厂商不存在: {vendor_id}"
            )
        
        adapter = self._get_adapter(vendor)
        
        try:
            if hasattr(adapter, 'query_image_task'):
                return adapter.query_image_task(task_id)
            elif hasattr(adapter, 'query_video_task'):
                return adapter.query_video_task(task_id)
            else:
                return TaskQueryResponse(
                    success=False,
                    task_id=task_id,
                    status="failed",
                    error="该厂商不支持任务查询"
                )
        except NotImplementedError:
            return TaskQueryResponse(
                success=False,
                task_id=task_id,
                status="failed",
                error="该厂商不支持任务查询"
            )
        except Exception as e:
            logger.error(f"任务查询失败: {e}")
            return TaskQueryResponse(
                success=False,
                task_id=task_id,
                status="failed",
                error=str(e)
            )
    
    def _get_adapter(self, vendor) -> BaseAdapter:
        if vendor.vendor_id not in self._adapter_cache:
            from src.adapters import get_adapter
            self._adapter_cache[vendor.vendor_id] = get_adapter(
                vendor.vendor_id, vendor
            )
        return self._adapter_cache[vendor.vendor_id]
    
    def clear_adapter_cache(self, vendor_id: str = None):
        if vendor_id:
            self._adapter_cache.pop(vendor_id, None)
        else:
            self._adapter_cache.clear()
