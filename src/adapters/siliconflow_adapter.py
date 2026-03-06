from typing import List
import requests
import time
import logging

from src.adapters.base_adapter import BaseAdapter
from src.models.vendor import VendorConfig
from src.models.response import GenerationResponse, AsyncGenerationResponse, TaskQueryResponse, ImageResult

logger = logging.getLogger(__name__)


class SiliconFlowAdapter(BaseAdapter):
    """硅基流动适配器 - 支持多种开源模型"""
    
    def generate_image(
        self,
        prompt: str,
        model: str = "FLUX.1-dev",
        negative_prompt: str = "",
        size: str = "1024x1024",
        **kwargs
    ) -> GenerationResponse:
        start_time = time.time()
        
        url = f"{self.base_url}/images/generations"
        headers = self._get_headers()
        
        width, height = self._parse_size(size)
        
        payload = {
            "model": model,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "size": f"{width}x{height}",
            "n": kwargs.get("n", 1),
            "response_format": "b64_json"
        }
        
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            data = self._handle_response(resp)
            
            images = data.get("data", [])
            results = []
            for img in images:
                results.append(ImageResult(
                    b64=img.get("b64_json", ""),
                    revised_prompt=img.get("revised_prompt", "")
                ))
            
            return GenerationResponse(
                success=True,
                data=results,
                model=model,
                processing_time=time.time() - start_time
            )
        except Exception as e:
            return GenerationResponse(success=False, error=str(e))
    
    def edit_image(
        self,
        image: str,
        prompt: str,
        model: str = None,
        mask: str = None,
        **kwargs
    ) -> GenerationResponse:
        return GenerationResponse(
            success=False,
            error="硅基流动当前不支持图像编辑功能"
        )
    
    def generate_video(
        self,
        prompt: str,
        model: str = None,
        duration: int = 5,
        **kwargs
    ) -> AsyncGenerationResponse:
        return AsyncGenerationResponse(
            success=False,
            error="硅基流动当前不支持视频生成功能"
        )
    
    def image_to_video(
        self,
        image: str,
        prompt: str = "",
        model: str = None,
        duration: int = 5,
        **kwargs
    ) -> AsyncGenerationResponse:
        return AsyncGenerationResponse(
            success=False,
            error="硅基流动当前不支持图生视频功能"
        )
    
    def query_video_task(self, task_id: str) -> TaskQueryResponse:
        return TaskQueryResponse(
            success=False,
            task_id=task_id,
            status="failed",
            error="不支持任务查询"
        )
    
    def list_models(self) -> List[str]:
        url = f"{self.base_url}/models"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            data = self._handle_response(resp)
            
            models = [m.get("id") for m in data.get("data", [])]
            return models
        except Exception as e:
            logger.error(f"获取模型列表失败: {e}")
            return ["FLUX.1-dev", "stable-diffusion-xl-base-1.0"]
