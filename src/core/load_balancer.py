from typing import List, Optional, Dict
from src.models.vendor import VendorConfig
from src.core.vendor_manager import VendorManager
from src.core.api_gateway import APIGateway
import logging

logger = logging.getLogger(__name__)


class LoadBalancer:
    """厂商负载均衡器 - 自动选择最优厂商"""
    
    def __init__(self, vendor_manager: VendorManager):
        self.vendor_manager = vendor_manager
        self._vendor_stats: Dict[str, Dict] = {}
    
    def select_vendor(
        self,
        task_type: str,
        exclude_vendors: List[str] = None
    ) -> Optional[VendorConfig]:
        available_vendors = self.vendor_manager.get_vendors_by_task_type(task_type)
        
        if not available_vendors:
            logger.warning(f"没有支持 {task_type} 的厂商")
            return None
        
        if exclude_vendors:
            available_vendors = [v for v in available_vendors if v.vendor_id not in exclude_vendors]
        
        if not available_vendors:
            return None
        
        vendor = self._select_by_strategy(available_vendors)
        
        if vendor:
            self._increment_request_count(vendor.vendor_id)
        
        return vendor
    
    def _select_by_strategy(self, vendors: List[VendorConfig]) -> VendorConfig:
        if not vendors:
            return None
        
        strategy = "priority"
        
        if strategy == "priority":
            return min(vendors, key=lambda v: v.priority)
        elif strategy == "round_robin":
            return self._round_robin_select(vendors)
        elif strategy == "least_used":
            return self._least_used_select(vendors)
        else:
            return vendors[0]
    
    def _round_robin_select(self, vendors: List[VendorConfig]) -> VendorConfig:
        vendor_counts = {v.vendor_id: self._vendor_stats.get(v.vendor_id, {}).get("request_count", 0) for v in vendors}
        min_count = min(vendor_counts.values())
        for v in vendors:
            if vendor_counts[v.vendor_id] == min_count:
                return v
        return vendors[0]
    
    def _least_used_select(self, vendors: List[VendorConfig]) -> VendorConfig:
        vendor_stats = {}
        for v in vendors:
            stats = self._vendor_stats.get(v.vendor_id, {})
            vendor_stats[v.vendor_id] = stats.get("success_count", 0) - stats.get("fail_count", 0) * 2
        
        best_vendor = max(vendor_stats.items(), key=lambda x: x[1])
        for v in vendors:
            if v.vendor_id == best_vendor[0]:
                return v
        return vendors[0]
    
    def _increment_request_count(self, vendor_id: str):
        if vendor_id not in self._vendor_stats:
            self._vendor_stats[vendor_id] = {
                "request_count": 0,
                "success_count": 0,
                "fail_count": 0
            }
        self._vendor_stats[vendor_id]["request_count"] += 1
    
    def record_success(self, vendor_id: str):
        if vendor_id not in self._vendor_stats:
            self._vendor_stats[vendor_id] = {
                "request_count": 0,
                "success_count": 0,
                "fail_count": 0
            }
        self._vendor_stats[vendor_id]["success_count"] += 1
    
    def record_failure(self, vendor_id: str):
        if vendor_id not in self._vendor_stats:
            self._vendor_stats[vendor_id] = {
                "request_count": 0,
                "success_count": 0,
                "fail_count": 0
            }
        self._vendor_stats[vendor_id]["fail_count"] += 1
    
    def get_vendor_stats(self, vendor_id: str = None) -> Dict:
        if vendor_id:
            return self._vendor_stats.get(vendor_id, {})
        return self._vendor_stats.copy()
    
    def reset_stats(self, vendor_id: str = None):
        if vendor_id:
            self._vendor_stats.pop(vendor_id, None)
        else:
            self._vendor_stats.clear()


class FailoverManager:
    """故障转移管理器 - 主厂商失败时自动切换"""
    
    def __init__(self, vendor_manager: VendorManager, load_balancer: LoadBalancer):
        self.vendor_manager = vendor_manager
        self.load_balancer = load_balancer
        self._failed_vendors: Dict[str, int] = {}
    
    def execute_with_failover(
        self,
        api_gateway: APIGateway,
        task_type: str,
        prompt: str,
        model: str = None,
        max_retries: int = 3,
        **kwargs
    ):
        exclude_vendors = set()
        
        for attempt in range(max_retries):
            vendor = self.load_balancer.select_vendor(task_type, list(exclude_vendors))
            
            if not vendor:
                return {
                    "success": False,
                    "error": f"没有可用的厂商，支持 {task_type} 类型"
                }
            
            logger.info(f"尝试厂商: {vendor.name} (尝试 {attempt + 1}/{max_retries})")
            
            try:
                if task_type in ["txt2vid", "img2vid"]:
                    response = api_gateway.generate_async(vendor.vendor_id, task_type, prompt, model, **kwargs)
                else:
                    response = api_gateway.generate(vendor.vendor_id, task_type, prompt, model, **kwargs)
                
                if response.success:
                    self.load_balancer.record_success(vendor.vendor_id)
                    self._failed_vendors.pop(vendor.vendor_id, None)
                    return response
                else:
                    self.load_balancer.record_failure(vendor.vendor_id)
                    exclude_vendors.add(vendor.vendor_id)
                    logger.warning(f"厂商 {vendor.name} 返回错误: {response.error}")
            
            except Exception as e:
                self.load_balancer.record_failure(vendor.vendor_id)
                exclude_vendors.add(vendor.vendor_id)
                self._failed_vendors[vendor.vendor_id] = self._failed_vendors.get(vendor.vendor_id, 0) + 1
                logger.error(f"厂商 {vendor.name} 请求异常: {e}")
        
        return {
            "success": False,
            "error": f"所有厂商均失败，已尝试 {max_retries} 次"
        }
    
    def get_failed_vendors(self) -> Dict[str, int]:
        return self._failed_vendors.copy()
    
    def clear_failed_vendor(self, vendor_id: str):
        self._failed_vendors.pop(vendor_id, None)
    
    def is_vendor_available(self, vendor_id: str) -> bool:
        fail_count = self._failed_vendors.get(vendor_id, 0)
        return fail_count < 3
