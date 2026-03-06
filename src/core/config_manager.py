import json
import os
from typing import Dict, List, Optional
from pathlib import Path
from src.models.vendor import VendorConfig
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器 - 负责配置文件加载和保存"""
    
    DEFAULT_CONFIG = {
        "version": "2.0.0",
        "default_vendor": "moark",
        "theme": "default",
        "language": "zh-CN",
        "ui_settings": {
            "default_size": "1024x1024",
            "available_sizes": ["512x512", "768x768", "1024x1024", "1280x720", "1920x1080"],
            "default_n": 1,
            "max_n": 4
        }
    }
    
    def __init__(self, config_file: str = "conf/config.json"):
        self.config_file = config_file
        self._config = None
    
    def load_config(self) -> dict:
        if self._config is not None:
            return self._config
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._config = {**self.DEFAULT_CONFIG, **data}
                    logger.info(f"加载配置文件: {self.config_file}")
                    return self._config
            except Exception as e:
                logger.error(f"加载配置文件失败: {e}")
        
        self._config = self.DEFAULT_CONFIG.copy()
        return self._config
    
    def save_config(self, config: dict):
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            self._config = config
            logger.info(f"保存配置文件: {self.config_file}")
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            raise
    
    def get_vendors_config(self) -> List[dict]:
        config = self.load_config()
        return config.get("vendors", [])
    
    def save_vendors_config(self, vendors: List[dict]):
        config = self.load_config()
        config["vendors"] = vendors
        self.save_config(config)
    
    def add_vendor_config(self, vendor_config: dict):
        vendors = self.get_vendors_config()
        vendor_id = vendor_config.get("vendor_id")
        
        for i, v in enumerate(vendors):
            if v.get("vendor_id") == vendor_id:
                vendors[i] = vendor_config
                break
        else:
            vendors.append(vendor_config)
        
        self.save_vendors_config(vendors)
    
    def remove_vendor_config(self, vendor_id: str):
        vendors = self.get_vendors_config()
        vendors = [v for v in vendors if v.get("vendor_id") != vendor_id]
        self.save_vendors_config(vendors)
    
    def get_vendor_config(self, vendor_id: str) -> Optional[dict]:
        vendors = self.get_vendors_config()
        for v in vendors:
            if v.get("vendor_id") == vendor_id:
                return v
        return None
    
    def get_default_vendor_id(self) -> str:
        config = self.load_config()
        return config.get("default_vendor", "moark")
    
    def set_default_vendor(self, vendor_id: str):
        config = self.load_config()
        config["default_vendor"] = vendor_id
        self.save_config(config)
    
    def get_ui_settings(self) -> dict:
        config = self.load_config()
        return config.get("ui_settings", self.DEFAULT_CONFIG["ui_settings"])
    
    def reload(self):
        self._config = None
        return self.load_config()
