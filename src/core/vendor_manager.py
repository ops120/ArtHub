from typing import Dict, List, Optional
from src.models.vendor import VendorConfig
import logging

logger = logging.getLogger(__name__)


class VendorManager:
    """厂商管理器 - 负责厂商的注册、查询、测试"""
    
    def __init__(self):
        self._vendors: Dict[str, VendorConfig] = {}
    
    def add_vendor(self, config: VendorConfig) -> bool:
        if config.vendor_id in self._vendors:
            logger.warning(f"厂商 {config.vendor_id} 已存在，将被覆盖")
        
        self._vendors[config.vendor_id] = config
        logger.info(f"添加厂商成功: {config.name}")
        return True
    
    def remove_vendor(self, vendor_id: str) -> bool:
        if vendor_id in self._vendors:
            del self._vendors[vendor_id]
            logger.info(f"移除厂商: {vendor_id}")
            return True
        return False
    
    def get_vendor(self, vendor_id: str) -> Optional[VendorConfig]:
        return self._vendors.get(vendor_id)
    
    def list_vendors(self, enabled_only: bool = False) -> List[VendorConfig]:
        vendors = list(self._vendors.values())
        if enabled_only:
            vendors = [v for v in vendors if v.enabled]
        return sorted(vendors, key=lambda x: x.priority)
    
    def update_vendor(self, vendor_id: str, **kwargs) -> bool:
        vendor = self.get_vendor(vendor_id)
        if not vendor:
            return False
        
        for key, value in kwargs.items():
            if hasattr(vendor, key):
                setattr(vendor, key, value)
        
        vendor.updated_at = datetime.now().isoformat()
        logger.info(f"更新厂商: {vendor_id}")
        return True
    
    def enable_vendor(self, vendor_id: str) -> bool:
        return self.update_vendor(vendor_id, enabled=True)
    
    def disable_vendor(self, vendor_id: str) -> bool:
        return self.update_vendor(vendor_id, enabled=False)
    
    def test_connection(self, vendor_id: str) -> Dict:
        vendor = self.get_vendor(vendor_id)
        if not vendor:
            return {"success": False, "message": "厂商不存在"}
        
        try:
            adapter = self._create_adapter(vendor)
            models = adapter.list_models()
            return {
                "success": True,
                "message": "连接成功",
                "models": models
            }
        except Exception as e:
            logger.error(f"厂商连接测试失败: {e}")
            return {"success": False, "message": str(e)}
    
    def _create_adapter(self, vendor: VendorConfig):
        from src.adapters import get_adapter
        return get_adapter(vendor.vendor_id, vendor)
    
    def reload_from_config(self, config_list: List[dict]):
        self._vendors.clear()
        for config_dict in config_list:
            vendor = VendorConfig.from_dict(config_dict)
            self._vendors[vendor.vendor_id] = vendor
        logger.info(f"重新加载了 {len(self._vendors)} 个厂商配置")
    
    def get_default_vendor(self) -> Optional[VendorConfig]:
        enabled_vendors = self.list_vendors(enabled_only=True)
        return enabled_vendors[0] if enabled_vendors else None
    
    def supports_task_type(self, vendor_id: str, task_type: str) -> bool:
        vendor = self.get_vendor(vendor_id)
        if not vendor:
            return False
        return vendor.supports_task(task_type)
    
    def get_vendors_by_task_type(self, task_type: str) -> List[VendorConfig]:
        vendors = self.list_vendors(enabled_only=True)
        return [v for v in vendors if v.supports_task(task_type)]


from datetime import datetime
