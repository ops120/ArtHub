from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging
import requests

logger = logging.getLogger(__name__)


class BaseAdapter(ABC):
    """AI 厂商适配器基类 - 所有厂商适配器需继承此类"""
    
    def __init__(self, config: 'VendorConfig'):
        self.config = config
        self.base_url = config.base_url
        self.api_key = config.api_key
        self.timeout = config.timeout
        self.max_retries = config.max_retries
        
        logger.info(f"初始化适配器: {config.name}")
    
    @abstractmethod
    def generate_image(
        self,
        prompt: str,
        model: str,
        **kwargs
    ) -> 'GenerationResponse':
        pass
    
    @abstractmethod
    def edit_image(
        self,
        image: str,
        prompt: str,
        model: str,
        mask: Optional[str] = None,
        **kwargs
    ) -> 'GenerationResponse':
        pass
    
    @abstractmethod
    def list_models(self) -> List[str]:
        pass
    
    def generate_video(
        self,
        prompt: str,
        model: str,
        duration: int = 5,
        **kwargs
    ) -> 'AsyncGenerationResponse':
        raise NotImplementedError(f"{self.config.name} 不支持文生视频")
    
    def image_to_video(
        self,
        image: str,
        prompt: str = "",
        model: str = None,
        duration: int = 5,
        **kwargs
    ) -> 'AsyncGenerationResponse':
        raise NotImplementedError(f"{self.config.name} 不支持图生视频")
    
    def query_video_task(self, task_id: str) -> 'TaskQueryResponse':
        raise NotImplementedError(f"{self.config.name} 不支持任务查询")
    
    def test_connection(self) -> bool:
        try:
            models = self.list_models()
            return len(models) > 0
        except Exception as e:
            logger.error(f"连接测试失败: {e}")
            return False
    
    def _parse_size(self, size_str: str) -> tuple:
        if 'x' in size_str:
            width, height = size_str.split('x')
            return int(width), int(height)
        return 1024, 1024
    
    def _handle_response(self, response: requests.Response) -> Dict:
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            raise Exception("API Key 无效或已过期")
        elif response.status_code == 429:
            raise Exception("请求频率超限，请稍后重试")
        elif response.status_code >= 500:
            raise Exception(f"服务器错误: {response.status_code}")
        else:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", response.text)
            except:
                error_msg = response.text
            raise Exception(f"请求失败: {error_msg}")
    
    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        if self.config.custom_headers:
            headers.update(self.config.custom_headers)
        return headers


from src.models.vendor import VendorConfig
from src.models.response import GenerationResponse, AsyncGenerationResponse, TaskQueryResponse
