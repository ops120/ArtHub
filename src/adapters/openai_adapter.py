from typing import List
import requests
import base64
import time

from src.adapters.base_adapter import BaseAdapter
from src.models.vendor import VendorConfig
from src.models.response import GenerationResponse, AsyncGenerationResponse, TaskQueryResponse, ImageResult


class OpenAIAdapter(BaseAdapter):
    """OpenAI DALL-E 适配器"""
    
    def generate_image(
        self,
        prompt: str,
        model: str = "dall-e-3",
        size: str = "1024x1024",
        quality: str = "standard",
        n: int = 1,
        **kwargs
    ) -> GenerationResponse:
        start_time = time.time()
        
        url = f"{self.base_url}/images/generations"
        headers = self._get_headers()
        
        size_map = {
            "1024x1024": "1024x1024",
            "512x512": "512x512",
            "256x256": "256x256",
            "1792x1024": "1792x1024",
            "1024x1792": "1024x1792"
        }
        
        payload = {
            "model": model,
            "prompt": prompt,
            "size": size_map.get(size, "1024x1024"),
            "n": n,
            "quality": quality if model == "dall-e-3" else "standard",
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
        model: str = "dall-e-2",
        mask: str = None,
        size: str = "1024x1024",
        n: int = 1,
        **kwargs
    ) -> GenerationResponse:
        return GenerationResponse(
            success=False,
            error="OpenAI DALL-E 不支持图像编辑功能"
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
            error="OpenAI DALL-E 不支持视频生成功能"
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
            error="OpenAI DALL-E 不支持图生视频功能"
        )
    
    def query_video_task(self, task_id: str) -> TaskQueryResponse:
        return TaskQueryResponse(
            success=False,
            task_id=task_id,
            status="failed",
            error="OpenAI DALL-E 不支持任务查询"
        )
    
    def list_models(self) -> List[str]:
        url = f"{self.base_url}/models"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            data = self._handle_response(resp)
            
            models = []
            for m in data.get("data", []):
                model_id = m.get("id", "")
                if "dall-e" in model_id.lower() or "gpt-image" in model_id.lower():
                    models.append(model_id)
            
            if not models:
                models = ["dall-e-3", "dall-e-2"]
            
            return models
        except Exception as e:
            logger.error(f"获取模型列表失败: {e}")
            return ["dall-e-3", "dall-e-2"]


import logging
logger = logging.getLogger(__name__)
