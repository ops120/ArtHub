# 白嫖大师 - 通用 AI 客户端需求说明

## 📋 文档信息

- **项目名称**：白嫖大师 - 通用 AI 客户端
- **版本**：v2.0 规划
- **作者**：ops120
- **最后更新**：2024年
- **文档状态**：开发指导文档

---

## 📑 目录

1. [项目背景与目标](#一项目背景与目标)
2. [目录结构](#二目录结构)
3. [系统架构](#三系统架构)
4. [核心模块设计](#四核心模块设计)
5. [数据结构设计](#五数据结构设计)
6. [接口规范](#六接口规范)
7. [界面设计](#七界面设计)
8. [工作流程](#八工作流程)
9. [错误处理](#九错误处理)
10. [开发计划](#十开发计划)
11. [测试方案](#十一测试方案)
12. [部署方案](#十二部署方案)
13. [附录](#十三附录)

---

## 一、项目背景与目标

### 1.1 当前状况
当前版本的"白嫖大师"仅支持 Moark 单一厂商的 AI 生成服务：
- ✅ 文生图
- ✅ 图像编辑
- ✅ 文生视频
- ✅ 图生视频
- ⚠️ 代码耦合度高，厂商切换困难

### 1.2 问题分析
```
当前架构问题：
┌─────────────────────────────────────────────────────────┐
│                      UI 层                              │
│  ┌─────────────────────────────────────────────────┐  │
│  │              moark_image_edit_ui.py             │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────────────┐  │  │
│  │  │ Moark   │ │ Moark   │ │    Moark        │  │  │
│  │  │ 文生图   │ │ 图像编辑 │ │    视频生成     │  │  │
│  │  └─────────┘ └─────────┘ └─────────────────┘  │  │
│  └─────────────────────────────────────────────────┘  │
│                           │                             │
│                           ▼                             │
│  ┌─────────────────────────────────────────────────┐  │
│  │              API 调用逻辑（硬编码）              │  │
│  │  base_url = "https://api.moark.com/v1"        │  │
│  │  API Key = 固定配置                            │  │
│  └─────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 1.3 目标愿景
将项目升级为**通用 AI 客户端**，支持：

| 目标 | 说明 |
|------|------|
| **多厂商支持** | 任意兼容 OpenAI API 规范的 AI 服务商 |
| **统一管理** | 集中管理所有厂商配置、API Key、模型列表 |
| **灵活扩展** | 新厂商接入无需修改核心代码 |
| **开箱即用** | 预设常用厂商配置模板 |
| **热插拔** | 运行时动态添加/移除厂商 |

---

## 二、目录结构

### 2.1 项目目录
```
白嫖大师/
├── moark_image_edit_ui.py     # 主程序入口（重构后）
├── 启动.cmd                   # Windows 启动脚本
├── requirements.txt           # Python 依赖
├── README.md                  # 项目说明
├── LICENSE                    # 许可证
│
├── docs/                      # 文档目录
│   └── 需求说明_通用AI客户端.md
│
├── conf/                      # 配置文件目录
│   ├── config.json            # 主配置文件（多厂商）
│   ├── config.example.json    # 配置示例
│   └── ui_settings.json      # UI 界面设置
│
├── src/                       # 源代码目录
│   ├── __init__.py
│   │
│   ├── core/                  # 核心模块
│   │   ├── __init__.py
│   │   ├── vendor_manager.py  # 厂商管理器
│   │   ├── model_manager.py   # 模型管理器
│   │   ├── api_gateway.py     # API 网关
│   │   ├── config_manager.py  # 配置管理器
│   │   ├── task_queue.py      # 任务队列
│   │   └── logger.py          # 日志模块
│   │
│   ├── adapters/              # 厂商适配器
│   │   ├── __init__.py
│   │   ├── base_adapter.py    # 适配器基类
│   │   ├── moark_adapter.py  # Moark 适配器
│   │   ├── openai_adapter.py  # OpenAI 适配器
│   │   ├── anthropic_adapter.py # Anthropic 适配器
│   │   └── custom_adapter.py  # 自定义适配器模板
│   │
│   ├── models/               # 数据模型
│   │   ├── __init__.py
│   │   ├── vendor.py         # 厂商数据模型
│   │   ├── task.py           # 任务数据模型
│   │   └── response.py       # 响应数据模型
│   │
│   ├── utils/                # 工具函数
│   │   ├── __init__.py
│   │   ├── http_client.py    # HTTP 客户端封装
│   │   ├── file_utils.py    # 文件工具
│   │   └── validators.py    # 数据验证
│   │
│   └── ui/                   # UI 组件
│       ├── __init__.py
│       ├── components.py      # 通用组件
│       ├── vendor_tab.py     # 厂商管理页面
│       ├── generate_tab.py   # 生成功能页面
│       └── config_tab.py     # 配置页面
│
├── templates/                 # 模板目录
│   └── vendor_templates.json  # 厂商预设模板
│
├── outputs/                   # 输出文件目录
│   └── {date}/
│
├── logs/                      # 日志目录
│
└── data/                      # 数据目录
    └── task_history.db        # 任务历史数据库
```

### 2.2 模块职责说明

| 目录/文件 | 职责 | 关键类/函数 |
|-----------|------|------------|
| `core/vendor_manager.py` | 厂商生命周期管理 | `VendorManager` |
| `core/api_gateway.py` | 统一 API 入口 | `APIGateway` |
| `adapters/base_adapter.py` | 适配器抽象基类 | `BaseAdapter` |
| `adapters/*_adapter.py` | 各厂商具体实现 | `MoarkAdapter` 等 |
| `models/vendor.py` | 厂商数据结构 | `VendorConfig` |
| `ui/vendor_tab.py` | 厂商管理界面 | `create_vendor_tab()` |

---

## 三、系统架构

### 3.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              用户交互层                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Gradio Web UI                                │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────┐ │   │
│  │  │ 厂商管理 │ │ 文生图  │ │ 图像编辑 │ │ 视频生成│ │任务历史│ │   │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └───┬───┘ │   │
│  └───────┼───────────┼───────────┼───────────┼───────────┼──────┘   │
└──────────┼───────────┼───────────┼───────────┼───────────┼──────────┘
           │           │           │           │           │
           ▼           ▼           ▼           ▼           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            业务逻辑层                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      API Gateway                                │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐   │   │
│  │  │ 任务分发器    │ │ 厂商路由器    │ │ 响应统一处理          │   │   │
│  │  └──────────────┘ └──────────────┘ └──────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐  │
│  │ 厂商管理器   │ │ 模型管理器   │ │ 配置管理器   │ │ 任务队列     │  │
│  │              │ │              │ │              │ │              │  │
│  │ add_vendor  │ │ list_models │ │ load_config │ │ add_task    │  │
│  │ remove_vend │ │ get_model   │ │ save_config │ │ query_task  │  │
│  │ test_connec │ │ refresh_    │ │ reload      │ │ get_status  │  │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
           │                              │
           ▼                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            适配器层                                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    BaseAdapter (抽象基类)                        │   │
│  │  ┌─────────────────────────────────────────────────────────┐   │   │
│  │  │ def generate_image()    def edit_image()               │   │   │
│  │  │ def generate_video()   def image_to_video()            │   │   │
│  │  │ def list_models()      def test_connection()          │   │   │
│  │  └─────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                    ▲              ▲              ▲              ▲         │
│        ┌──────────┴───┐  ┌──────┴─────┐  ┌───┴────────┐  ┌┴────────┐ │
│        │ MoarkAdapter │  │OpenAIAdapter│  │AnthropicAd│  │CustomAdp│ │
│        │   图/视频    │  │   DALL-E    │  │   Claude  │  │  自定义  │ │
│        └──────────────┘  └─────────────┘  └───────────┘  └─────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
           │              │              │              │
           ▼              ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            外部服务层                                    │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐  │
│  │   Moark      │ │   OpenAI     │ │  Anthropic   │ │   Other     │  │
│  │   API        │ │   API        │ │    API       │ │    API      │  │
│  │ api.moark.com│ │ api.openai.co│ │api.anthropic.│ │   xxxxxx    │  │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 数据流图

```
用户请求流程：
┌────────┐     ┌────────────┐     ┌────────────┐     ┌───────────┐
│  用户   │────▶│   UI 接收   │────▶│ API Gateway │────▶│ 适配器    │
└────────┘     └────────────┘     └────────────┘     └─────┬─────┘
                                                            │
                              ┌────────────┐                │
                              │ 返回结果    │◀───────────────┘
                              └─────┬──────┘
                                    │
                              ┌─────▼──────┐
                              │  UI 展示    │
                              └────────────┘
```

### 3.3 厂商添加流程

```
新增厂商流程：
┌─────────┐     ┌────────────┐     ┌────────────┐     ┌──────────┐
│ 选择模板 │────▶│ 填写配置   │────▶│  测试连接  │────▶│ 保存配置 │
└─────────┘     └────────────┘     └─────┬──────┘     └──────────┘
                                          │
                              ┌───────────┴───────────┐
                              │                       │
                         ┌────▼────┐            ┌───▼────┐
                         │  连接成功 │            │ 连接失败│
                         └─────────┘            └────────┘
```

---

## 四、核心模块设计

### 4.1 厂商管理器 (VendorManager)

**文件**：`src/core/vendor_manager.py`

**职责**：
- 厂商的增删改查
- 厂商连接测试
- 厂商状态管理

**核心代码**：
```python
from typing import Dict, List, Optional
from src.models.vendor import VendorConfig
import logging

logger = logging.getLogger(__name__)

class VendorManager:
    """厂商管理器 - 负责厂商的注册、查询、测试"""
    
    def __init__(self):
        self._vendors: Dict[str, VendorConfig] = {}
    
    def add_vendor(self, config: VendorConfig) -> bool:
        """
        添加新厂商
        
        Args:
            config: 厂商配置对象
            
        Returns:
            bool: 是否添加成功
        """
        if config.vendor_id in self._vendors:
            logger.warning(f"厂商 {config.vendor_id} 已存在，将被覆盖")
        
        self._vendors[config.vendor_id] = config
        logger.info(f"添加厂商成功: {config.name}")
        return True
    
    def remove_vendor(self, vendor_id: str) -> bool:
        """移除厂商"""
        if vendor_id in self._vendors:
            del self._vendors[vendor_id]
            logger.info(f"移除厂商: {vendor_id}")
            return True
        return False
    
    def get_vendor(self, vendor_id: str) -> Optional[VendorConfig]:
        """获取厂商配置"""
        return self._vendors.get(vendor_id)
    
    def list_vendors(self, enabled_only: bool = False) -> List[VendorConfig]:
        """
        列出所有厂商
        
        Args:
            enabled_only: 是否只返回启用的厂商
            
        Returns:
            List[VendorConfig]: 厂商配置列表
        """
        vendors = list(self._vendors.values())
        if enabled_only:
            vendors = [v for v in vendors if v.enabled]
        return vendors
    
    def test_connection(self, vendor_id: str) -> Dict[str, any]:
        """
        测试厂商连接
        
        Returns:
            Dict: {
                "success": bool,
                "message": str,
                "models": List[str]  # 如果成功，返回模型列表
            }
        """
        vendor = self.get_vendor(vendor_id)
        if not vendor:
            return {"success": False, "message": "厂商不存在"}
        
        try:
            # 创建适配器并测试
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
        """根据厂商配置创建适配器"""
        from src.adapters import get_adapter
        return get_adapter(vendor.vendor_id, vendor)
    
    def reload_from_config(self, config_list: List[dict]):
        """从配置重新加载厂商"""
        self._vendors.clear()
        for config_dict in config_list:
            vendor = VendorConfig(**config_dict)
            self._vendors[vendor.vendor_id] = vendor
        logger.info(f"重新加载了 {len(self._vendors)} 个厂商配置")
```

### 4.2 适配器基类 (BaseAdapter)

**文件**：`src/adapters/base_adapter.py`

**职责**：
- 定义厂商适配器的标准接口
- 提供通用方法实现

**核心代码**：
```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from openai import OpenAI
import logging
import requests

logger = logging.getLogger(__name__)

class BaseAdapter(ABC):
    """AI 厂商适配器基类 - 所有厂商适配器需继承此类"""
    
    def __init__(self, config: 'VendorConfig'):
        """
        初始化适配器
        
        Args:
            config: 厂商配置对象
        """
        self.config = config
        self.base_url = config.base_url
        self.api_key = config.api_key
        self.timeout = config.timeout
        self.max_retries = config.max_retries
        
        # 初始化 OpenAI 兼容客户端
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=self.timeout,
            max_retries=self.max_retries
        )
        
        logger.info(f"初始化适配器: {config.name}")
    
    # ==================== 抽象方法（子类必须实现） ====================
    
    @abstractmethod
    def generate_image(
        self,
        prompt: str,
        model: str,
        **kwargs
    ) -> 'GenerationResponse':
        """
        文生图
        
        Args:
            prompt: 提示词
            model: 模型名称
            **kwargs: 其他参数
            
        Returns:
            GenerationResponse: 生成响应
        """
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
        """
        图像编辑
        
        Args:
            image: 图像（base64 或 URL）
            prompt: 提示词
            model: 模型名称
            mask: 蒙版（可选）
            
        Returns:
            GenerationResponse: 生成响应
        """
        pass
    
    @abstractmethod
    def list_models(self) -> List[str]:
        """获取模型列表"""
        pass
    
    # ==================== 可选方法（子类可重写） ====================
    
    def generate_video(
        self,
        prompt: str,
        model: str,
        duration: int = 5,
        **kwargs
    ) -> 'AsyncGenerationResponse':
        """
        文生视频（默认实现，子类可重写）
        """
        raise NotImplementedError(f"{self.config.name} 不支持文生视频")
    
    def image_to_video(
        self,
        image: str,
        prompt: str = "",
        model: str = None,
        duration: int = 5,
        **kwargs
    ) -> 'AsyncGenerationResponse':
        """
        图生视频（默认实现，子类可重写）
        """
        raise NotImplementedError(f"{self.config.name} 不支持图生视频")
    
    def test_connection(self) -> bool:
        """
        测试连接（默认实现，子类可重写）
        """
        try:
            models = self.list_models()
            return len(models) > 0
        except Exception as e:
            logger.error(f"连接测试失败: {e}")
            return False
    
    # ==================== 通用方法 ====================
    
    def _parse_size(self, size_str: str) -> tuple:
        """解析尺寸字符串为 (width, height)"""
        if 'x' in size_str:
            width, height = size_str.split('x')
            return int(width), int(height)
        return 1024, 1024
    
    def _handle_response(self, response: requests.Response) -> Dict:
        """处理 HTTP 响应"""
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            raise Exception("API Key 无效或已过期")
        elif response.status_code == 429:
            raise Exception("请求频率超限，请稍后重试")
        elif response.status_code >= 500:
            raise Exception(f"服务器错误: {response.status_code}")
        else:
            raise Exception(f"请求失败: {response.text}")
```

### 4.3 API 网关 (APIGateway)

**文件**：`src/core/api_gateway.py`

**职责**：
- 统一入口，分发请求到对应适配器
- 请求参数标准化
- 响应格式统一

**核心代码**：
```python
from typing import Dict, Any, Optional
from src.core.vendor_manager import VendorManager
from src.adapters.base_adapter import BaseAdapter
from src.models.response import GenerationResponse, AsyncGenerationResponse
import logging

logger = logging.getLogger(__name__)

class TaskType:
    """任务类型常量"""
    TEXT2IMG = "text2img"      # 文生图
    IMAGE_EDIT = "edit"        # 图像编辑
    TEXT2VIDEO = "txt2vid"     # 文生视频
    IMAGE2VIDEO = "img2vid"    # 图生视频

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
        """
        统一生成接口
        
        Args:
            vendor_id: 厂商 ID
            task_type: 任务类型
            prompt: 提示词
            model: 模型名称
            **kwargs: 其他参数
            
        Returns:
            GenerationResponse: 统一格式的响应
        """
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
            elif task_type == TaskType.TEXT2VIDEO:
                return adapter.generate_video(prompt, model, **kwargs)
            elif task_type == TaskType.IMAGE2VIDEO:
                return adapter.image_to_video(
                    image=kwargs.get("image"),
                    prompt=prompt,
                    model=model,
                    **kwargs
                )
            else:
                return GenerationResponse(
                    success=False,
                    error=f"不支持的任务类型: {task_type}"
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
        """
        异步生成接口 - 适用于视频生成等耗时任务
        """
        vendor = self.vendor_manager.get_vendor(vendor_id)
        if not vendor:
            return AsyncGenerationResponse(
                success=False,
                error=f"厂商不存在: {vendor_id}"
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
            else:
                return AsyncGenerationResponse(
                    success=False,
                    error=f"该任务类型不支持异步: {task_type}"
                )
        except Exception as e:
            logger.error(f"异步生成失败: {e}")
            return AsyncGenerationResponse(success=False, error=str(e))
    
    def _get_adapter(self, vendor) -> BaseAdapter:
        """获取或创建适配器（带缓存）"""
        if vendor.vendor_id not in self._adapter_cache:
            from src.adapters import get_adapter
            self._adapter_cache[vendor.vendor_id] = get_adapter(
                vendor.vendor_id, vendor
            )
        return self._adapter_cache[vendor.vendor_id]
```

### 4.4 厂商适配器示例 (MoarkAdapter)

**文件**：`src/adapters/moark_adapter.py`

**职责**：
- 实现 Moark 厂商特定逻辑
- 映射通用接口到 Moark API

**核心代码**：
```python
from typing import List, Dict, Any
from src.adapters.base_adapter import BaseAdapter
from src.models.vendor import VendorConfig
from src.models.response import GenerationResponse, AsyncGenerationResponse
import requests
import base64
import json

class MoarkAdapter(BaseAdapter):
    """Moark 模力方舟适配器"""
    
    SUPPORTED_TASK_TYPES = ["text2img", "edit", "txt2vid", "img2vid"]
    
    def generate_image(
        self,
        prompt: str,
        model: str = "z-image-turbo",
        negative_prompt: str = "",
        size: str = "1024x1024",
        **kwargs
    ) -> GenerationResponse:
        """文生图"""
        import time
        start_time = time.time()
        
        url = f"{self.base_url}/images/generations"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
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
                results.append({
                    "b64": img.get("b64_json", ""),
                    "revised_prompt": img.get("revised_prompt", "")
                })
            
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
        """图像编辑"""
        import time
        start_time = time.time()
        
        url = f"{self.base_url}/images/edits"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        
        files = {}
        data = {"prompt": prompt, "model": model}
        
        # 处理图像
        if image.startswith("data:image"):
            # base64 编码的图像
            img_data = image.split(",", 1)[1]
            files["image"] = ("image.png", base64.b64decode(img_data), "image/png")
        else:
            # URL
            files["image"] = ("image.png", requests.get(image).content, "image/png")
        
        # 处理蒙版
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
            results = [{"b64": img.get("b64_json", "")} for img in images]
            
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
        """文生视频 - 异步"""
        url = f"{self.base_url}/async/videos/generations"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
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
        """图生视频 - 异步"""
        url = f"{self.base_url}/async/videos/image-to-video"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "prompt": prompt,
            "image_url": image,
            "duration": duration,
            "mode": "image-to-video"  # 必须参数
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
    
    def list_models(self) -> List[str]:
        """获取模型列表"""
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
```

### 4.5 适配器注册机制

**文件**：`src/adapters/__init__.py`

```python
from src.adapters.base_adapter import BaseAdapter
from src.adapters.moark_adapter import MoarkAdapter
from src.adapters.openai_adapter import OpenAIAdapter

# 适配器注册表
ADAPTER_REGISTRY = {
    "moark": MoarkAdapter,
    "openai": OpenAIAdapter,
    # 添加更多适配器
}

def get_adapter(vendor_id: str, config) -> BaseAdapter:
    """
    获取适配器实例
    
    Args:
        vendor_id: 厂商 ID
        config: 厂商配置
        
    Returns:
        BaseAdapter: 适配器实例
    """
    adapter_class = ADAPTER_REGISTRY.get(vendor_id)
    if not adapter_class:
        raise ValueError(f"不支持的厂商: {vendor_id}")
    return adapter_class(config)

def register_adapter(vendor_id: str, adapter_class: type):
    """
    注册新的适配器
    
    Args:
        vendor_id: 厂商 ID
        adapter_class: 适配器类
    """
    ADAPTER_REGISTRY[vendor_id] = adapter_class
```

---

## 五、数据结构设计

### 5.1 数据模型文件

**文件**：`src/models/vendor.py`
```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

@dataclass
class VendorConfig:
    """厂商配置数据模型"""
    
    # 必需字段
    vendor_id: str           # 唯一标识，如 "moark", "openai"
    name: str               # 显示名称
    base_url: str           # API 基础地址
    api_key: str            # API Key
    
    # 可选字段
    description: str = ""    # 描述
    enabled: bool = True     # 是否启用
    priority: int = 100      # 优先级（数字越小越高）
    
    # 支持的功能
    support_text2img: bool = False
    support_edit: bool = False
    support_txt2vid: bool = False
    support_img2vid: bool = False
    
    # 模型配置
    text2img_models: List[str] = field(default_factory=list)
    edit_models: List[str] = field(default_factory=list)
    txt2vid_models: List[str] = field(default_factory=list)
    img2vid_models: List[str] = field(default_factory=list)
    
    # 连接配置
    timeout: int = 60
    max_retries: int = 3
    custom_headers: Dict[str, str] = field(default_factory=dict)
    
    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "vendor_id": self.vendor_id,
            "name": self.name,
            "base_url": self.base_url,
            "api_key": self.api_key,
            "description": self.description,
            "enabled": self.enabled,
            "priority": self.priority,
            "support_text2img": self.support_text2img,
            "support_edit": self.support_edit,
            "support_txt2vid": self.support_txt2vid,
            "support_img2vid": self.support_img2vid,
            "text2img_models": self.text2img_models,
            "edit_models": self.edit_models,
            "txt2vid_models": self.txt2vid_models,
            "img2vid_models": self.img2vid_models,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "custom_headers": self.custom_headers,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'VendorConfig':
        """从字典创建"""
        return cls(**data)
```

### 5.2 响应数据模型

**文件**：`src/models/response.py`
```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class ImageResult:
    """单张图像结果"""
    b64: Optional[str] = None      # Base64 编码
    url: Optional[str] = None      # URL 地址
    revised_prompt: Optional[str] = None  # 优化后的提示词

@dataclass
class GenerationResponse:
    """同步生成响应"""
    success: bool
    data: List[ImageResult] = field(default_factory=list)
    error: Optional[str] = None
    model: Optional[str] = None
    processing_time: Optional[float] = None
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": [
                {
                    "b64": img.b64,
                    "url": img.url,
                    "revised_prompt": img.revised_prompt
                }
                for img in self.data
            ],
            "error": self.error,
            "model": self.model,
            "processing_time": self.processing_time
        }

@dataclass
class AsyncGenerationResponse:
    """异步生成响应"""
    success: bool
    task_id: Optional[str] = None
    status: str = "pending"  # pending, processing, completed, failed
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "task_id": self.task_id,
            "status": self.status,
            "error": self.error
        }

@dataclass
class TaskQueryResponse:
    """任务查询响应"""
    success: bool
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: Optional[float] = None  # 0.0 - 1.0
```

### 5.3 配置文件结构

**文件**：`conf/config.json`
```json
{
  "version": "2.0.0",
  "default_vendor": "moark",
  "theme": "default",
  "language": "zh-CN",
  
  "vendors": [
    {
      "vendor_id": "moark",
      "name": "模力方舟",
      "base_url": "https://api.moark.com/v1",
      "api_key": "your-api-key",
      "enabled": true,
      "priority": 100,
      "description": "支持文生图、图像编辑、文生视频、图生视频",
      "support_text2img": true,
      "support_edit": true,
      "support_txt2vid": true,
      "support_img2vid": true,
      "text2img_models": [
        "FLUX.1-dev",
        "LongCat-Image",
        "flux-1-schnell",
        "Qwen-Image-2512"
      ],
      "edit_models": [
        "LongCat-Image-Edit",
        "Qwen-Image-Edit-2511"
      ],
      "txt2vid_models": [
        "stepvideo-t2v",
        "Wan2.1-T2V-1.3B"
      ],
      "img2vid_models": [
        "LTX-2"
      ],
      "timeout": 60,
      "max_retries": 3
    },
    {
      "vendor_id": "openai",
      "name": "OpenAI",
      "base_url": "https://api.openai.com/v1",
      "api_key": "sk-...",
      "enabled": true,
      "priority": 90,
      "description": "DALL-E 图像生成",
      "support_text2img": true,
      "text2img_models": [
        "dall-e-3",
        "dall-e-2"
      ],
      "timeout": 120,
      "max_retries": 3
    }
  ],
  
  "ui_settings": {
    "default_size": "1024x1024",
    "available_sizes": [
      "512x512",
      "768x768",
      "1024x1024",
      "1280x720",
      "1920x1080"
    ],
    "default_n": 1,
    "max_n": 4
  }
}
```

### 5.4 厂商预设模板

**文件**：`templates/vendor_templates.json`
```json
{
  "templates": [
    {
      "vendor_id": "moark",
      "name": "模力方舟",
      "base_url": "https://api.moark.com/v1",
      "support_text2img": true,
      "support_edit": true,
      "support_txt2vid": true,
      "support_img2vid": true,
      "default_models": {
        "text2img": "FLUX.1-dev",
        "edit": "Qwen-Image-Edit",
        "txt2vid": "stepvideo-t2v",
        "img2vid": "LTX-2"
      }
    },
    {
      "vendor_id": "openai",
      "name": "OpenAI",
      "base_url": "https://api.openai.com/v1",
      "support_text2img": true,
      "default_models": {
        "text2img": "dall-e-3"
      }
    },
    {
      "vendor_id": "anthropic",
      "name": "Anthropic",
      "base_url": "https://api.anthropic.com/v1",
      "support_text2img": false,
      "description": "Claude 大模型"
    },
    {
      "vendor_id": "dashscope",
      "name": "阿里云 DashScope",
      "base_url": "https://dashscope.aliyuncs.com/api/v1",
      "support_text2img": true,
      "default_models": {
        "text2img": "wanx-style-transfer"
      }
    },
    {
      "vendor_id": "siliconflow",
      "name": "硅基流动",
      "base_url": "https://api.siliconflow.cn/v1",
      "support_text2img": true,
      "default_models": {
        "text2img": "FLUX.1-dev"
      }
    },
    {
      "vendor_id": "volcengine",
      "name": "火山引擎",
      "base_url": "https://ark.cn-beijing.volces.com/api/v3",
      "support_text2img": true,
      "default_models": {
        "text2img": "doubao-image-generation"
      }
    }
  ]
}
```

---

## 六、接口规范

### 6.1 核心接口定义

#### 6.1.1 文生图接口
```python
def generate_image(
    prompt: str,                    # 提示词（必需）
    model: str = None,              # 模型名称（必需）
    negative_prompt: str = "",       # 负提示词
    size: str = "1024x1024",        # 图像尺寸
    quality: str = "standard",      # 质量 (standard/hd)
    n: int = 1,                     # 生成数量
    style: str = None,              # 风格（厂商特定）
    **vendor_kwargs                 # 厂商特定参数
) -> GenerationResponse:
    """
    文生图接口
    
    Returns:
        GenerationResponse:
        {
            "success": True,
            "data": [
                {
                    "b64": "iVBORw0KGgo...",
                    "url": "https://...",
                    "revised_prompt": "..."
                }
            ],
            "model": "FLUX.1-dev",
            "processing_time": 2.5
        }
    """
```

#### 6.1.2 图像编辑接口
```python
def edit_image(
    image: str,                     # 图像 (base64 或 URL)
    prompt: str,                    # 编辑指令
    model: str = None,              # 模型名称
    mask: str = None,               # 蒙版 (base64 或 URL)
    **vendor_kwargs
) -> GenerationResponse:
    """
    图像编辑接口
    
    支持模式：
    1. 提示词编辑：仅传入 prompt
    2. 局部编辑：传入 prompt + mask
    """
```

#### 6.1.3 文生视频接口
```python
def generate_video(
    prompt: str,                    # 提示词
    model: str = None,              # 模型名称
    duration: int = 5,             # 时长（秒）
    aspect_ratio: str = "16:9",     # 宽高比
    **vendor_kwargs
) -> AsyncGenerationResponse:
    """
    文生视频接口（异步）
    
    Returns:
        AsyncGenerationResponse:
        {
            "success": True,
            "task_id": "task_xxxxx",
            "status": "pending"
        }
    """
```

#### 6.1.4 图生视频接口
```python
def image_to_video(
    image: str,                     # 图像 (base64 或 URL)
    prompt: str = "",               # 可选提示词
    model: str = None,              # 模型名称
    duration: int = 5,             # 时长
    **vendor_kwargs
) -> AsyncGenerationResponse:
    """
    图生视频接口（异步）
    """
```

#### 6.1.5 任务查询接口
```python
def query_task(
    task_id: str                    # 任务 ID
) -> TaskQueryResponse:
    """
    查询异步任务状态
    
    Returns:
        TaskQueryResponse:
        {
            "success": True,
            "task_id": "task_xxxxx",
            "status": "completed",  # pending/processing/completed/failed
            "result": {
                "video_url": "https://...",
                "preview_url": "https://..."
            },
            "progress": 1.0,
            "error": None
        }
    """
```

---

## 七、界面设计

### 7.1 主界面布局

```
┌────────────────────────────────────────────────────────────────────────┐
│                    🎨 白嫖大师 - 通用 AI 客户端                          │
│                    作者：你们喜爱的老王  |  v2.0                        │
├────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐ │
│  │   🏠 厂商管理  │ │   🖼️ 文生图   │ │   ✏️ 图像编辑  │ │  🎬 视频   │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘ │
│  ┌──────────────────────────────────────────┐ ┌────────────────────┐ │
│  │                                          │ │   ⚙️ 配置            │ │
│  │           📋 任务历史                     │ │                     │ │
│  └──────────────────────────────────────────┘ └────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

### 7.2 厂商管理页面

```
┌──────────────────────────────────────────────────────────────────────┐
│  🏠 厂商管理                                                        │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  当前使用厂商：  [模力方舟 ▼]  状态：✅ 已连接                         │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  已添加的厂商                                                  │ │
│  │  ┌────────┬────────┬──────────┬──────────┬─────────────────┐  │ │
│  │  │ 厂商名 │ 状态   │ 功能支持 │ 模型数量 │ 操作             │  │ │
│  │  ├────────┼────────┼──────────┼──────────┼─────────────────┤  │ │
│  │  │ 模力方舟│ ✅启用 │ 图/视频  │ 8        │ [测试][编辑][删] │  │ │
│  │  │ OpenAI │ ✅启用 │ 图像     │ 2        │ [测试][编辑][删] │  │ │
│  │  │ 火山引擎│ ❌禁用 │ 图像     │ 1        │ [测试][编辑][删] │  │ │
│  │  └────────┴────────┴──────────┴──────────┴─────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  [+ 添加新厂商]                                                      │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 7.3 添加厂商对话框

```
┌──────────────────────────────────────────────────────────────────────┐
│  添加新厂商                                                [X]       │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  快速开始：                                                          │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  选择模板：[模力方舟 ▼]  [OpenAI ▼]  [阿里云]  [自定义]       │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  基础配置：                                                          │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  厂商 ID：     [________________________] (如: moark)          │ │
│  │  显示名称：    [________________________] (如: 模力方舟)     │ │
│  │  API 地址：    [________________________]                    │ │
│  │  API Key：    [________________________]                     │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  支持功能：  ☑ 文生图  ☑ 图像编辑  ☑ 文生视频  ☑ 图生视频        │
│                                                                      │
│  模型配置：                                                          │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  文生图模型： [FLUX.1-dev        ▼] [+添加更多]              │ │
│  │  编辑模型：   [Qwen-Image-Edit  ▼] [+添加更多]              │ │
│  │  视频模型：   [stepvideo-t2v    ▼] [+添加更多]              │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  高级设置：                                                          │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  超时时间：   [60] 秒                                          │ │
│  │  最大重试：   [3] 次                                           │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│                     [取消]                      [保存并测试]         │
└──────────────────────────────────────────────────────────────────────┘
```

### 7.4 生成功能页面（文生图示例）

```
┌──────────────────────────────────────────────────────────────────────┐
│  🖼️ 文生图                                                        │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  选择厂商：  [模力方舟 ▼]  [OpenAI ▼]                         │ │
│  │  选择模型：  [FLUX.1-dev ▼]                                   │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────┬──────────────────────────────────┐ │
│  │  提示词：                  │                                  │ │
│  │  ┌──────────────────────┐ │                                  │ │
│  │  │ 一只可爱的猫咪在花园  │ │                                  │ │
│  │  │ 中玩耍，阳光明媚    │ │        ┌────────────────────┐   │ │
│  │  └──────────────────────┘ │        │                    │   │ │
│  │                            │        │   [生成图像预览]    │   │ │
│  │  负提示词：                │        │                    │   │ │
│  │  ┌──────────────────────┐ │        │                    │   │ │
│  │  │ ugly, blurry,       │ │        └────────────────────┘   │ │
│  │  │ low quality         │ │                                  │ │
│  │  └──────────────────────┘ │                                  │ │
│  │                            │                                  │ │
│  │  图像尺寸： [1024x1024 ▼]  │                                  │ │
│  │  生成数量： [1]            │                                  │ │
│  │  图像质量： [standard ▼]   │                                  │ │
│  └────────────────────────────┴──────────────────────────────────┘ │
│                                                                      │
│  [🚀 立即生成]  [⏳ 异步生成（适合视频）]                           │
│                                                                      │
│  生成结果：                                                          │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  ✅ 生成成功！ 耗时: 2.5秒                                     │ │
│  │  [下载图像]  [复制 Base64]                                    │ │
│  └────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 八、工作流程

### 8.1 厂商添加流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                        厂商添加流程                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. 用户点击 [添加新厂商]                                            │
│         │                                                           │
│         ▼                                                           │
│  2. 选择预设模板 OR 填写自定义配置                                    │
│         │                                                           │
│         ├─ 选择模板：自动填充 URL、支持的模型等                        │
│         │                                                           │
│         └─ 自定义：手动填写所有配置                                   │
│         │                                                           │
│         ▼                                                           │
│  3. 填写 API Key 和配置                                             │
│         │                                                           │
│         ▼                                                           │
│  4. 点击 [保存并测试]                                                │
│         │                                                           │
│         ▼                                                           │
│  5. 后端执行测试：                                                   │
│     ┌───────────────────┐                                          │
│     │ 调用 adapter.      │                                          │
│     │ list_models()      │                                          │
│     │ 测试 API 连接      │                                          │
│     └─────────┬─────────┘                                          │
│               │                                                     │
│       ┌───────┴───────┐                                            │
│       │               │                                            │
│   ┌───▼───┐      ┌────▼────┐                                       │
│   │ 成功  │      │  失败   │                                       │
│   └───┬───┘      └────┬────┘                                       │
│       │               │                                             │
│       ▼               ▼                                             │
│  保存配置      返回错误信息                                           │
│  显示在列表    允许重试                                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 8.2 图像生成流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                       图像生成流程                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  用户在 UI 填写参数                                                  │
│  ├── 厂商选择                                                       │
│  ├── 模型选择                                                       │
│  ├── 提示词                                                        │
│  └── 其他参数                                                       │
│         │                                                           │
│         ▼                                                           │
│  调用 APIGateway.generate()                                         │
│         │                                                           │
│         ▼                                                           │
│  根据厂商 ID 获取适配器                                              │
│  adapter = get_adapter(vendor_id, config)                          │
│         │                                                           │
│         ▼                                                           │
│  调用具体生成方法                                                    │
│  response = adapter.generate_image(prompt, model, ...)             │
│         │                                                           │
│         ▼                                                           │
│  处理响应                                                           │
│  ├── 成功：返回图像数据                                              │
│  ├── 失败：返回错误信息                                              │
│  └── 异常：捕获并记录日志                                           │
│         │                                                           │
│         ▼                                                           │
│  UI 展示结果                                                        │
│  ├── 显示图像/错误信息                                               │
│  └── 记录到任务历史                                                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 九、错误处理

### 9.1 错误分类

| 错误类型 | 错误码 | 说明 | 处理方式 |
|---------|-------|------|---------|
| VALIDATION_ERROR | 400 | 参数验证失败 | 返回具体错误信息 |
| AUTH_ERROR | 401 | 认证失败 | 提示检查 API Key |
| RATE_LIMIT | 429 | 频率超限 | 自动重试或提示用户 |
| SERVER_ERROR | 500+ | 服务器错误 | 重试机制 |
| NETWORK_ERROR | -1 | 网络错误 | 重试机制 |
| TIMEOUT_ERROR | -2 | 请求超时 | 增加超时时间重试 |
| VENDOR_NOT_FOUND | 404 | 厂商不存在 | 提示配置错误 |
| NOT_SUPPORTED | 501 | 功能不支持 | 提示厂商能力限制 |

### 9.2 错误响应格式

```python
{
    "success": False,
    "error": {
        "code": "AUTH_ERROR",
        "message": "API Key 无效或已过期",
        "details": {}
    }
}
```

### 9.3 重试机制

```python
def retry_with_backoff(
    func,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0
):
    """指数退避重试"""
    delay = initial_delay
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            logger.warning(f"请求失败，{delay}秒后重试: {e}")
            time.sleep(delay)
            delay *= backoff_factor
```

---

## 十、开发计划

### 10.1 第一阶段：基础框架 (MVP)

**目标**：实现最小可用产品，支持 Moark 厂商

| 序号 | 任务 | 文件 | 预计行数 |
|-----|------|------|---------|
| 1 | 创建项目目录结构 | 目录创建 | - |
| 2 | 实现数据模型 | `src/models/*.py` | ~200 |
| 3 | 实现厂商管理器 | `src/core/vendor_manager.py` | ~150 |
| 4 | 实现适配器基类 | `src/adapters/base_adapter.py` | ~100 |
| 5 | 实现 Moark 适配器 | `src/adapters/moark_adapter.py` | ~300 |
| 6 | 实现 API 网关 | `src/core/api_gateway.py` | ~150 |
| 7 | 实现配置管理器 | `src/core/config_manager.py` | ~100 |
| 8 | 重构主 UI | `moark_image_edit_ui.py` | ~500 |

**里程碑**：能够通过 UI 添加 Moark 厂商并成功生成图像

### 10.2 第二阶段：功能完善

| 序号 | 任务 | 说明 |
|-----|------|------|
| 1 | 添加 OpenAI 适配器 | 支持 DALL-E |
| 2 | 添加厂商测试功能 | 连接测试 |
| 3 | 添加模型列表自动获取 | 调用 API 获取模型 |
| 4 | 完善错误处理 | 统一错误处理 |
| 5 | 异步任务支持 | 视频生成轮询 |

**里程碑**：支持 2+ 厂商，完整生成流程

### 10.3 第三阶段：高级功能

| 序号 | 任务 | 说明 |
|-----|------|------|
| 1 | 厂商负载均衡 | 多厂商轮询 |
| 2 | 自动故障转移 | 主厂商失败自动切换 |
| 3 | 使用统计 | 记录使用量 |
| 4 | API Key 加密 | 安全存储 |

### 10.4 第四阶段：生态扩展

| 序号 | 任务 | 说明 |
|-----|------|------|
| 1 | 添加更多厂商适配器 | 阿里云、硅基流动等 |
| 2 | 插件系统 | 扩展点设计 |
| 3 | Docker 支持 | 容器化部署 |
| 4 | API 暴露 | 供其他应用调用 |

---

## 十一、测试方案

### 11.1 单元测试

```python
# tests/test_vendor_manager.py
import pytest
from src.core.vendor_manager import VendorManager
from src.models.vendor import VendorConfig

def test_add_vendor():
    manager = VendorManager()
    config = VendorConfig(
        vendor_id="test",
        name="测试厂商",
        base_url="https://api.test.com",
        api_key="test-key"
    )
    assert manager.add_vendor(config) == True
    assert manager.get_vendor("test") is not None

def test_remove_vendor():
    manager = VendorManager()
    # ...
```

### 11.2 集成测试

```python
# tests/test_moark_adapter.py
import pytest
from src.adapters.moark_adapter import MoarkAdapter
from src.models.vendor import VendorConfig

def test_generate_image():
    config = VendorConfig(
        vendor_id="moark",
        name="Moark",
        base_url="https://api.moark.com/v1",
        api_key="test-key"
    )
    adapter = MoarkAdapter(config)
    response = adapter.generate_image(
        prompt="a cat",
        model="FLUX.1-dev"
    )
    assert response.success == True
    assert len(response.data) > 0
```

### 11.3 测试覆盖目标

| 模块 | 目标覆盖率 |
|------|----------|
| core | 80%+ |
| models | 90%+ |
| adapters | 80%+ |
| utils | 80%+ |

---

## 十二、部署方案

### 12.1 本地部署

```bash
# 1. 克隆项目
git clone https://github.com/ops120/bai-piao-master.git
cd bai-piao-master

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 复制配置
cp conf/config.example.json conf/config.json
# 编辑 config.json 填入 API Key

# 5. 启动
python moark_image_edit_ui.py
```

### 12.2 Docker 部署

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 11111

CMD ["python", "moark_image_edit_ui.py", "--server-port", "11111"]
```

```bash
# docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "11111:11111"
    volumes:
      - ./conf:/app/conf
      - ./outputs:/app/outputs
      - ./logs:/app/logs
    restart: unless-stopped
```

---

## 十三、附录

### 13.1 术语表

| 术语 | 英文 | 说明 |
|------|------|------|
| 厂商 | Vendor | AI 服务提供商 |
| 适配器 | Adapter | 厂商对接代码 |
| API 网关 | API Gateway | 统一入口 |
| 任务类型 | Task Type | 图生图、文生视频等 |
| 异步任务 | Async Task | 需要轮询的任务 |

### 13.2 兼容厂商列表

| 厂商 | base_url | 支持功能 |
|------|----------|---------|
| 模力方舟 | https://api.moark.com/v1 | 图/视频 |
| OpenAI | https://api.openai.com/v1 | 图像 |
| 阿里云 | https://dashscope.aliyuncs.com/api/v1 | 图像 |
| 硅基流动 | https://api.siliconflow.cn/v1 | 图像 |
| 火山引擎 | https://ark.cn-beijing.volces.com/api/v3 | 图像 |

### 13.3 配置检查清单

- [ ] Python 3.8+
- [ ] requests 库
- [ ] openai 库
- [ ] gradio 库
- [ ] 配置文件正确填写
- [ ] API Key 有效

---

## ✅ 总结

本文档详细描述了**白嫖大师通用 AI 客户端**的完整需求：

| 章节 | 关键内容 |
|------|---------|
| 目录结构 | 清晰的模块划分，便于维护 |
| 系统架构 | 四层架构，职责明确 |
| 核心模块 | VendorManager、APIGateway、Adapter |
| 数据结构 | 完整的数据模型设计 |
| 接口规范 | 统一的 API 接口定义 |
| 界面设计 | 用户友好的交互设计 |
| 开发计划 | 四阶段迭代开发 |
| 测试方案 | 单元测试 + 集成测试 |
| 部署方案 | 本地 + Docker |

**下一步**：开始第一阶段开发，实现最小可用产品。

---

*文档版本：1.0*
*最后更新：2024年*
*作者：ops120*
