import requests
from typing import Optional, Dict, Any
import time


class HttpClient:
    def __init__(self, timeout: int = 30, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
    
    def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict] = None,
        json: Optional[Dict] = None,
        data: Any = None,
        files: Optional[Dict] = None,
        **kwargs
    ) -> requests.Response:
        delay = 1.0
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=json,
                    data=data,
                    files=files,
                    timeout=self.timeout,
                    **kwargs
                )
                return response
            except requests.exceptions.Timeout as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(delay)
                    delay *= 2
            except requests.exceptions.ConnectionError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(delay)
                    delay *= 2
            except requests.exceptions.RequestException as e:
                raise e
        
        raise last_error
    
    def get(self, url: str, headers: Optional[Dict] = None, **kwargs) -> requests.Response:
        return self.request("GET", url, headers=headers, **kwargs)
    
    def post(
        self,
        url: str,
        headers: Optional[Dict] = None,
        json: Optional[Dict] = None,
        data: Any = None,
        files: Optional[Dict] = None,
        **kwargs
    ) -> requests.Response:
        return self.request("POST", url, headers=headers, json=json, data=data, files=files, **kwargs)
    
    def close(self):
        self.session.close()


def download_file(url: str, save_path: str, headers: Optional[Dict] = None) -> bool:
    try:
        response = requests.get(url, headers=headers, stream=True, timeout=60)
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return True
    except Exception:
        return False


def encode_image_base64(image_path: str) -> str:
    import base64
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def decode_base64_image(base64_str: str, save_path: str) -> bool:
    import base64
    try:
        image_data = base64.b64decode(base64_str)
        with open(save_path, 'wb') as f:
            f.write(image_data)
        return True
    except Exception:
        return False
