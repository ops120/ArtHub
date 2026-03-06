from src.adapters.base_adapter import BaseAdapter
from src.adapters.moark_adapter import MoarkAdapter
from src.adapters.openai_adapter import OpenAIAdapter
from src.adapters.siliconflow_adapter import SiliconFlowAdapter

ADAPTER_REGISTRY = {
    "moark": MoarkAdapter,
    "openai": OpenAIAdapter,
    "siliconflow": SiliconFlowAdapter,
}


def get_adapter(vendor_id: str, config) -> BaseAdapter:
    adapter_class = ADAPTER_REGISTRY.get(vendor_id)
    if not adapter_class:
        raise ValueError(f"不支持的厂商: {vendor_id}")
    return adapter_class(config)


def register_adapter(vendor_id: str, adapter_class: type):
    ADAPTER_REGISTRY[vendor_id] = adapter_class


def get_supported_vendors() -> list:
    return list(ADAPTER_REGISTRY.keys())


def is_vendor_supported(vendor_id: str) -> bool:
    return vendor_id in ADAPTER_REGISTRY
