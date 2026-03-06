from typing import List
import requests
import base64
import time

from src.adapters.base_adapter import BaseAdapter
from src.models.vendor import VendorConfig
from src.models.response import GenerationResponse, AsyncGenerationResponse, TaskQueryResponse, ImageResult


class MoarkAdapter(BaseAdapter):
    """Moark 模力方舟适配器"""
    
    def generate_image(
        self,
        prompt: str,
        model: str = "z-image-turbo",
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
        model: str = "Qwen-Image-Edit",
        mask: str = None,
        **kwargs
    ) -> GenerationResponse:
        start_time = time.time()
        
        url = f"{self.base_url}/images/edits"
        headers = self._get_headers()
        
        files = {}
        data = {"prompt": prompt, "model": model}
        
        if image.startswith("data:image"):
            img_data = image.split(",", 1)[1]
            files["image"] = ("image.png", base64.b64decode(img_data), "image/png")
        else:
            files["image"] = ("image.png", requests.get(image).content, "image/png")
        
        if mask:
            if mask.startswith("data:image"):
                mask_data = mask.split(",", 1)[1]
                files["mask"] = ("mask.png", base64.b64decode(mask_data), "image/png")
            else:
                files["mask"] = ("mask.png", requests.get(mask).content, "image/png")
        
        try:
            resp = requests.post(url, data=data, files=files, headers=headers, timeout=self.timeout)
            result_data = self._handle_response(resp)
            
            images = result_data.get("data", [])
            results = [ImageResult(b64=img.get("b64_json", "")) for img in images]
            
            return GenerationResponse(
                success=True,
                data=results,
                model=model,
                processing_time=time.time() - start_time
            )
        except Exception as e:
            return GenerationResponse(success=False, error=str(e))
    
    def generate_video(
        self,
        prompt: str,
        model: str = "stepvideo-t2v",
        duration: int = 5,
        **kwargs
    ) -> AsyncGenerationResponse:
        async_url = self.base_url.replace("/v1", "") if "/v1" in self.base_url else self.base_url
        url = f"{async_url}/async/videos/generations"
        headers = self._get_headers()
        
        payload = {
            "model": model,
            "prompt": prompt,
            "duration": duration
        }
        
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            data = self._handle_response(resp)
            
            return AsyncGenerationResponse(
                success=True,
                task_id=data.get("task_id"),
                status=data.get("status", "pending")
            )
        except Exception as e:
            return AsyncGenerationResponse(success=False, error=str(e))
    
    def image_to_video(
        self,
        image: str,
        prompt: str = "",
        model: str = "LTX-2",
        duration: int = 5,
        **kwargs
    ) -> AsyncGenerationResponse:
        async_url = self.base_url.replace("/v1", "") if "/v1" in self.base_url else self.base_url
        url = f"{async_url}/async/videos/image-to-video"
        headers = self._get_headers()
        
        payload = {
            "model": model,
            "prompt": prompt,
            "image_url": image if image.startswith("http") else None,
            "duration": duration,
            "mode": "image-to-video"
        }
        
        if not payload["image_url"]:
            return AsyncGenerationResponse(
                success=False,
                error="图生视频需要提供有效的图片URL"
            )
        
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            data = self._handle_response(resp)
            
            return AsyncGenerationResponse(
                success=True,
                task_id=data.get("task_id"),
                status=data.get("status", "pending")
            )
        except Exception as e:
            return AsyncGenerationResponse(success=False, error=str(e))
    
    def generate_image_async(
        self,
        prompt: str,
        model: str = "FLUX.1-dev",
        negative_prompt: str = "",
        size: str = "1024x1024",
        n: int = 1,
        **kwargs
    ) -> AsyncGenerationResponse:
        async_url = self.base_url.replace("/v1", "") if "/v1" in self.base_url else self.base_url
        url = f"{async_url}/async/images/generations"
        headers = self._get_headers()
        
        payload = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "n": n,
            "response_format": "b64_json"
        }
        
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            data = self._handle_response(resp)
            
            return AsyncGenerationResponse(
                success=True,
                task_id=data.get("task_id"),
                status=data.get("status", "pending")
            )
        except Exception as e:
            return AsyncGenerationResponse(success=False, error=str(e))
    
    def edit_image_async(
        self,
        prompt: str,
        image: str,
        model: str = "LongCat-Image-Edit",
        mask: str = None,
        size: str = "1024x1024",
        **kwargs
    ) -> AsyncGenerationResponse:
        async_url = self.base_url.replace("/v1", "") if "/v1" in self.base_url else self.base_url
        url = f"{async_url}/async/images/edits"
        headers = self._get_headers()
        
        if not image:
            return AsyncGenerationResponse(success=False, error="需要提供图片")
        
        payload = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "response_format": "b64_json"
        }
        
        if image.startswith("data:image") or len(image) > 200:
            payload["image"] = image
        else:
            payload["image_url"] = image
        
        if mask:
            if mask.startswith("data:image") or len(mask) > 200:
                payload["mask"] = mask
            else:
                payload["mask_url"] = mask
        
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            data = self._handle_response(resp)
            
            return AsyncGenerationResponse(
                success=True,
                task_id=data.get("task_id"),
                status=data.get("status", "pending")
            )
        except Exception as e:
            return AsyncGenerationResponse(success=False, error=str(e))
    
    def query_image_task(self, task_id: str) -> TaskQueryResponse:
        url = f"https://moark.com/api/v1/task/{task_id}"
        headers = self._get_headers()
        
        try:
            resp = requests.get(url, headers=headers, timeout=self.timeout)
            data = self._handle_response(resp)
            
            status = data.get("status", "pending")
            
            output = data.get("output", {})
            image_b64 = output.get("b64_json") or output.get("image")
            
            if not image_b64:
                file_url = output.get("file_url") or output.get("url")
                if file_url:
                    return TaskQueryResponse(
                        success=True,
                        task_id=task_id,
                        status=status,
                        result={"file_url": file_url, "url": file_url}
                    )
            
            return TaskQueryResponse(
                success=True,
                task_id=task_id,
                status=status,
                result={"image": image_b64} if image_b64 else None
            )
        except Exception as e:
            return TaskQueryResponse(
                success=False,
                task_id=task_id,
                status="failed",
                error=str(e)
            )
    
    def query_video_task(self, task_id: str) -> TaskQueryResponse:
        url = f"https://moark.com/api/v1/task/{task_id}"
        headers = self._get_headers()
        
        try:
            resp = requests.get(url, headers=headers, timeout=self.timeout)
            data = self._handle_response(resp)
            
            status = data.get("status", "pending")
            
            result_data = data.get("result", {})
            download_url = result_data.get("url") or result_data.get("video_url")
            preview_url = result_data.get("preview_url")
            
            progress_map = {
                "pending": 0.0,
                "processing": 0.5,
                "completed": 1.0,
                "failed": 1.0
            }
            
            return TaskQueryResponse(
                success=True,
                task_id=task_id,
                status=status,
                progress=progress_map.get(status, 0.0),
                download_url=download_url,
                preview_url=preview_url,
                result=result_data
            )
        except Exception as e:
            return TaskQueryResponse(
                success=False,
                task_id=task_id,
                status="failed",
                error=str(e)
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
            return []
