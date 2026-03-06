import json
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path


class UsageStats:
    """使用统计 - 记录和分析 API 使用情况"""
    
    def __init__(self, stats_file: str = "data/usage_stats.json"):
        self.stats_file = stats_file
        self._ensure_data_dir()
        self._stats = self._load_stats()
    
    def _ensure_data_dir(self):
        Path(self.stats_file).parent.mkdir(parents=True, exist_ok=True)
    
    def _load_stats(self) -> dict:
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return {
            "total_requests": 0,
            "total_success": 0,
            "total_fail": 0,
            "by_vendor": {},
            "by_task_type": {},
            "by_date": {},
            "daily_stats": []
        }
    
    def _save_stats(self):
        with open(self.stats_file, "w", encoding="utf-8") as f:
            json.dump(self._stats, f, ensure_ascii=False, indent=2)
    
    def record_request(
        self,
        vendor_id: str,
        task_type: str,
        success: bool,
        duration: float = 0
    ):
        today = datetime.now().strftime("%Y-%m-%d")
        
        self._stats["total_requests"] += 1
        if success:
            self._stats["total_success"] += 1
        else:
            self._stats["total_fail"] += 1
        
        if vendor_id not in self._stats["by_vendor"]:
            self._stats["by_vendor"][vendor_id] = {
                "requests": 0,
                "success": 0,
                "fail": 0,
                "total_duration": 0
            }
        
        self._stats["by_vendor"][vendor_id]["requests"] += 1
        if success:
            self._stats["by_vendor"][vendor_id]["success"] += 1
        else:
            self._stats["by_vendor"][vendor_id]["fail"] += 1
        self._stats["by_vendor"][vendor_id]["total_duration"] += duration
        
        if task_type not in self._stats["by_task_type"]:
            self._stats["by_task_type"][task_type] = {
                "requests": 0,
                "success": 0,
                "fail": 0
            }
        
        self._stats["by_task_type"][task_type]["requests"] += 1
        if success:
            self._stats["by_task_type"][task_type]["success"] += 1
        else:
            self._stats["by_task_type"][task_type]["fail"] += 1
        
        if today not in self._stats["by_date"]:
            self._stats["by_date"][today] = {
                "requests": 0,
                "success": 0,
                "fail": 0
            }
        
        self._stats["by_date"][today]["requests"] += 1
        if success:
            self._stats["by_date"][today]["success"] += 1
        else:
            self._stats["by_date"][today]["fail"] += 1
        
        self._save_stats()
    
    def get_summary(self) -> dict:
        return {
            "total_requests": self._stats["total_requests"],
            "total_success": self._stats["total_success"],
            "total_fail": self._stats["total_fail"],
            "success_rate": (
                self._stats["total_success"] / self._stats["total_requests"] * 100
                if self._stats["total_requests"] > 0 else 0
            )
        }
    
    def get_vendor_stats(self) -> dict:
        return self._stats["by_vendor"]
    
    def get_task_type_stats(self) -> dict:
        return self._stats["by_task_type"]
    
    def get_daily_stats(self, days: int = 7) -> dict:
        result = {}
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            result[date] = self._stats["by_date"].get(date, {
                "requests": 0,
                "success": 0,
                "fail": 0
            })
        return result
    
    def get_vendor_leaderboard(self, limit: int = 10) -> List[dict]:
        vendors = []
        for vendor_id, stats in self._stats["by_vendor"].items():
            vendors.append({
                "vendor_id": vendor_id,
                "requests": stats["requests"],
                "success": stats["success"],
                "fail": stats["fail"],
                "avg_duration": stats["total_duration"] / stats["requests"] if stats["requests"] > 0 else 0
            })
        
        vendors.sort(key=lambda x: x["requests"], reverse=True)
        return vendors[:limit]
    
    def reset_stats(self):
        self._stats = {
            "total_requests": 0,
            "total_success": 0,
            "total_fail": 0,
            "by_vendor": {},
            "by_task_type": {},
            "by_date": {},
            "daily_stats": []
        }
        self._save_stats()
    
    def export_stats(self) -> dict:
        return self._stats.copy()
