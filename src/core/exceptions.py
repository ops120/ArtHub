from typing import Optional, Dict, Any


class AIError(Exception):
    def __init__(self, message: str, code: str = None, details: Dict = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": {
                "message": self.message,
                "code": self.code,
                "details": self.details
            }
        }


class ValidationError(AIError):
    def __init__(self, message: str, details: Dict = None):
        super().__init__(message, "VALIDATION_ERROR", details)


class AuthError(AIError):
    def __init__(self, message: str = "认证失败，请检查 API Key", details: Dict = None):
        super().__init__(message, "AUTH_ERROR", details)


class RateLimitError(AIError):
    def __init__(self, message: str = "请求频率超限，请稍后重试", details: Dict = None):
        super().__init__(message, "RATE_LIMIT", details)


class ServerError(AIError):
    def __init__(self, message: str = "服务器错误", details: Dict = None):
        super().__init__(message, "SERVER_ERROR", details)


class NetworkError(AIError):
    def __init__(self, message: str = "网络错误", details: Dict = None):
        super().__init__(message, "NETWORK_ERROR", details)


class TimeoutError(AIError):
    def __init__(self, message: str = "请求超时", details: Dict = None):
        super().__init__(message, "TIMEOUT_ERROR", details)


class VendorNotFoundError(AIError):
    def __init__(self, vendor_id: str, details: Dict = None):
        message = f"厂商不存在: {vendor_id}"
        super().__init__(message, "VENDOR_NOT_FOUND", details)


class NotSupportedError(AIError):
    def __init__(self, message: str, details: Dict = None):
        super().__init__(message, "NOT_SUPPORTED", details)


ERROR_CODES = {
    400: ValidationError,
    401: AuthError,
    403: AuthError,
    404: VendorNotFoundError,
    429: RateLimitError,
    500: ServerError,
    502: ServerError,
    503: ServerError,
    504: TimeoutError,
}


def get_error_class(status_code: int) -> type:
    return ERROR_CODES.get(status_code, AIError)


def raise_error(status_code: int, message: str = None, details: Dict = None):
    error_class = get_error_class(status_code)
    if message is None:
        message = f"HTTP {status_code} 错误"
    raise error_class(message, details)
