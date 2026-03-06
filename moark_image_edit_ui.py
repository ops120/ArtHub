# moark_image_edit_ui.py
# 白嫖大师 - 图像视频生成工具
# 作者：你们喜爱的老王
# B 站：https://space.bilibili.com/97727630

import gradio as gr
import requests
import json
import os
import io
import base64
import sqlite3
import shutil
import logging
from PIL import Image
import mimetypes
from datetime import datetime
from pathlib import Path
import zipfile

# =============================================
# 日志配置
# =============================================
def setup_logging():
    """配置日志系统"""
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    log_file = logs_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

logger = setup_logging()
logger.info("应用启动中...")

# =============================================
# SQLite 数据库管理
# =============================================
DB_FILE = "task_history.db"

def init_db():
    """初始化 SQLite 数据库"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 创建任务表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT UNIQUE NOT NULL,
            task_type TEXT NOT NULL,
            prompt TEXT,
            model TEXT,
            size TEXT,
            status TEXT DEFAULT 'waiting',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            result TEXT,
            file_url TEXT,
            download_path TEXT
        )
    ''')
    
    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_id ON tasks(task_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON tasks(created_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_type ON tasks(task_type)')
    
    conn.commit()
    conn.close()

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def db_add_task(task_id, task_type, prompt, model, size, status="waiting"):
    """添加任务到数据库"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    now = datetime.now().isoformat()
    try:
        cursor.execute('''
            INSERT INTO tasks (task_id, task_type, prompt, model, size, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (task_id, task_type, prompt, model, size, status, now, now))
        conn.commit()
    except sqlite3.IntegrityError:
        # 任务已存在，更新状态
        cursor.execute('''
            UPDATE tasks SET status = ?, updated_at = ?
            WHERE task_id = ?
        ''', (status, now, task_id))
        conn.commit()
    finally:
        conn.close()

def db_update_task_status(task_id, status, result=None, file_url=None):
    """更新任务状态"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    now = datetime.now().isoformat()
    cursor.execute('''
        UPDATE tasks SET status = ?, updated_at = ?, result = ?, file_url = ?
        WHERE task_id = ?
    ''', (status, now, json.dumps(result, ensure_ascii=False) if result else None, file_url, task_id))
    
    conn.commit()
    conn.close()

def db_get_tasks(date_str=None, task_type=None, limit=100):
    """获取任务列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM tasks WHERE 1=1"
    params = []
    
    if date_str:
        query += " AND created_at LIKE ?"
        params.append(f"{date_str}%")
    
    if task_type and task_type != "all":
        query += " AND task_type = ?"
        params.append(task_type)
    
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def db_get_all_dates():
    """获取所有可用日期"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT DISTINCT DATE(created_at) as date
        FROM tasks
        ORDER BY date DESC
    ''')
    
    dates = [row['date'] for row in cursor.fetchall()]
    conn.close()
    return dates

def db_get_task_by_id(task_id):
    """根据 Task ID 获取任务"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM tasks WHERE task_id = ?', (task_id,))
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None

def db_clear_history():
    """清空历史记录"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tasks')
    conn.commit()
    conn.close()

# 初始化数据库
init_db()

# =============================================
# 任务历史记录管理 (兼容旧版本，使用 SQLite)
# =============================================
TASK_HISTORY_FILE = "task_history.json"

def load_task_history():
    """加载任务历史记录 (兼容旧版本)"""
    return db_get_tasks(limit=1000)

def save_task_history(history):
    """保存任务历史记录 (兼容旧版本，实际使用 SQLite)"""
    pass  # SQLite 已自动保存

def add_task_to_history(task_id, task_type, prompt, model, size, status="waiting"):
    """添加任务到历史记录"""
    db_add_task(task_id, task_type, prompt, model, size, status)
    return db_get_tasks(limit=100)

def update_task_status(task_id, status, result=None, file_url=None):
    """更新任务状态"""
    db_update_task_status(task_id, status, result, file_url)
    return db_get_tasks(limit=100)

def get_tasks_by_date_and_type(history, date_str=None, task_type=None):
    """按日期和类型筛选任务"""
    if not date_str and not task_type:
        return history
    
    filtered = []
    for task in history:
        # 按日期筛选
        if date_str:
            task_date = task["created_at"][:10]  # 获取 YYYY-MM-DD
            if task_date != date_str:
                continue
        
        # 按类型筛选
        if task_type and task_type != "all":
            if task["task_type"] != task_type:
                continue
        
        filtered.append(task)
    
    return filtered

def get_available_dates(history):
    """获取所有可用的日期列表"""
    dates = set()
    for task in history:
        date_str = task["created_at"][:10]
        dates.add(date_str)
    return sorted(list(dates), reverse=True)

# =============================================
# 配置管理
# =============================================
# 配置文件路径 (conf 目录)
CONFIG_FILE = os.path.join("conf", "moark_config.json")

DEFAULT_CONFIG = {
    "base_url": "https://api.moark.com/v1",
    "api_key": "",
    "text2img_model": "z-image-turbo",  # 文生图默认模型
    "edit_model": "Qwen-Image-Edit",     # 图生图/编辑默认模型
    "timeout": 180,                       # 默认超时时间（秒）
    "default_size": "1024x1024",          # 默认输出尺寸
    "available_sizes": [                   # 可用尺寸列表
        "512x512", "768x768", "1024x1024", 
        "1280x768", "768x1280", "1280x960", 
        "960x1280", "1440x1440", "1536x1024", 
        "1024x1536"
    ],
    "async_txt2img_models": [
        "FLUX.1-dev",
        "LongCat-Image",
        "flux-1-schnell",
        "Qwen-Image-2512",
        "Z-Image",
        "Qwen-Image"
    ],
    "async_edit_models": [
        "LongCat-Image-Edit",
        "Qwen-Image-Edit-2511",
        "FLUX.1-Kontext-dev"
    ],
    "async_txt2vid_models": [
        "stepvideo-t2v"
    ],
    "async_img2vid_models": [
        "LTX-2"
    ]
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 兼容旧配置
                if "default_model" in data and "text2img_model" not in data:
                    data["text2img_model"] = data["default_model"]
                    data["edit_model"] = data["default_model"]
                return {**DEFAULT_CONFIG, **data}
        except:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

# =============================================
# 文生图函数 (纯文本生成)
# =============================================
def generate_text_to_image(
    prompt,
    negative_prompt="",
    model="z-image-turbo",
    size="1024x1024",
    n=1,
    response_format="b64_json",
    base_url="https://api.moark.com/v1",
    api_key="",
    timeout=180,
):
    """使用 /images/generations 接口进行纯文生图"""
    if not prompt.strip():
        return "请输入提示词", None
    if not api_key.strip():
        return "请配置 API Key", None

    url = f"{base_url.rstrip('/')}/images/generations"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "prompt": prompt.strip(),
        "n": n,
        "size": size,
        "response_format": response_format,
    }
    
    # 添加负提示词（如果提供）
    if negative_prompt and negative_prompt.strip():
        payload["negative_prompt"] = negative_prompt.strip()

    try:
        print(f"文生图请求到: {url}")
        print(f"使用模型: {model}")
        print(f"输出尺寸: {size}")
        print(f"超时设置: {timeout}秒")
        print(f"请求数据: {payload}")
        
        resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
        
        print(f"响应状态码: {resp.status_code}")
        
        if resp.status_code != 200:
            error_msg = f"生成失败 (HTTP {resp.status_code})"
            try:
                error_detail = resp.json()
                error_msg += f"\n{json.dumps(error_detail, indent=2, ensure_ascii=False)}"
            except:
                error_msg += f"\n{resp.text[:500]}"
            return error_msg, None
        
        resp.raise_for_status()
        result = resp.json()
        return process_generation_response(result)
        
    except requests.exceptions.Timeout:
        return f"请求超时（{timeout}秒），请增加超时时间或稍后重试", None
    except requests.exceptions.ConnectionError:
        return "连接错误，请检查网络", None
    except Exception as e:
        err_text = resp.text if 'resp' in locals() else ""
        return f"生成失败：{str(e)}\n{err_text}", None


def process_generation_response(result):
    """处理生成接口的响应"""
    try:
        images = result.get("data", [])
        if not images:
            return f"响应无图像数据：{json.dumps(result, indent=2, ensure_ascii=False)}", None

        # 处理 b64_json 格式
        if "b64_json" in images[0]:
            img_bytes = base64.b64decode(images[0]["b64_json"])
            return "生成成功", Image.open(io.BytesIO(img_bytes))
        
        # 处理 url 格式
        elif "url" in images[0]:
            img_resp = requests.get(images[0]["url"], timeout=30)
            img_resp.raise_for_status()
            return "生成成功", Image.open(io.BytesIO(img_resp.content))
        
        else:
            return f"未知响应格式：{json.dumps(result, indent=2, ensure_ascii=False)}", None
            
    except Exception as e:
        return f"处理响应失败：{str(e)}", None


# =============================================
# 图像编辑函数（使用 /images/edits 接口）
# =============================================
def edit_image(
    prompt,
    image=None,
    mask=None,
    model="Qwen-Image-Edit",
    n=1,
    size="1024x1024",
    response_format="b64_json",
    base_url="https://api.moark.com/v1",
    api_key="",
    timeout=180,
):
    """使用 /images/edits 接口进行图像编辑/图生图"""
    if not prompt.strip():
        return "请输入提示词", None
    if not api_key.strip():
        return "请配置 API Key", None
    if image is None:
        return "请上传要编辑的图像", None

    url = f"{base_url.rstrip('/')}/images/edits"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
    }

    try:
        # 将 PIL Image 转换为 bytes
        img_buffer = io.BytesIO()
        image.save(img_buffer, format="PNG")
        img_bytes = img_buffer.getvalue()
        
        # 准备 multipart/form-data
        files = {
            'image': ('image.png', img_bytes, 'image/png'),
        }
        
        # 如果有 mask 图像
        if mask is not None:
            mask_buffer = io.BytesIO()
            mask.save(mask_buffer, format="PNG")
            files['mask'] = ('mask.png', mask_buffer.getvalue(), 'image/png')
        
        # 准备表单数据
        data = {
            'model': model,
            'prompt': prompt.strip(),
            'n': str(n),
            'response_format': response_format,
        }
        
        # 如果有 size 参数且不为空
        if size and size.strip():
            data['size'] = size
            
        print(f"编辑请求到: {url}")
        print(f"使用模型: {model}")
        print(f"输出尺寸: {size}")
        print(f"超时设置: {timeout}秒")
        print(f"表单数据: {data}")
        print(f"文件: {list(files.keys())}")
        
        # 发送请求
        resp = requests.post(
            url, 
            files=files, 
            data=data, 
            headers=headers, 
            timeout=timeout
        )
        
        print(f"响应状态码: {resp.status_code}")
        print(f"响应头: {dict(resp.headers)}")
        
        if resp.status_code != 200:
            error_msg = f"编辑失败 (HTTP {resp.status_code})"
            try:
                error_detail = resp.json()
                error_msg += f"\n{json.dumps(error_detail, indent=2, ensure_ascii=False)}"
            except:
                error_msg += f"\n{resp.text[:500]}"
            return error_msg, None
        
        resp.raise_for_status()
        result = resp.json()
        return process_edit_response(result)
        
    except requests.exceptions.Timeout:
        return f"请求超时（{timeout}秒），请增加超时时间或稍后重试", None
    except requests.exceptions.ConnectionError:
        return "连接错误，请检查网络", None
    except Exception as e:
        err_text = resp.text if 'resp' in locals() else ""
        return f"编辑失败：{str(e)}\n{err_text}", None


def process_edit_response(result):
    """处理编辑接口的响应"""
    try:
        images = result.get("data", [])
        if not images:
            return f"响应无图像数据：{json.dumps(result, indent=2, ensure_ascii=False)}", None

        # 处理 b64_json 格式
        if "b64_json" in images[0]:
            img_bytes = base64.b64decode(images[0]["b64_json"])
            return "编辑成功", Image.open(io.BytesIO(img_bytes))
        
        # 处理 url 格式
        elif "url" in images[0]:
            img_resp = requests.get(images[0]["url"], timeout=30)
            img_resp.raise_for_status()
            return "编辑成功", Image.open(io.BytesIO(img_resp.content))
        
        else:
            return f"未知响应格式：{json.dumps(result, indent=2, ensure_ascii=False)}", None
            
    except Exception as e:
        return f"处理响应失败：{str(e)}", None


# =============================================
# 备用的 URL 参考图生成
# =============================================
def generate_with_reference(
    prompt,
    negative_prompt="",
    model="Qwen-Image-Edit",
    size="1024x1024",
    n=1,
    reference_url="",
    base_url="https://api.moark.com/v1",
    api_key="",
    response_format="url",
    timeout=180,
):
    """使用 /images/generations 接口 + 参考图 URL"""
    if not prompt.strip():
        return "请输入提示词", None
    if not api_key.strip():
        return "请配置 API Key", None
    if not reference_url.strip().startswith(("http://", "https://")):
        return "请提供有效的参考图 URL", None

    url = f"{base_url.rstrip('/')}/images/generations"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "prompt": prompt.strip(),
        "n": n,
        "size": size,
        "response_format": response_format,
        "image": reference_url.strip(),
    }
    
    # 添加负提示词（如果提供）
    if negative_prompt and negative_prompt.strip():
        payload["negative_prompt"] = negative_prompt.strip()

    try:
        print(f"URL参考图请求到: {url}")
        print(f"使用模型: {model}")
        print(f"输出尺寸: {size}")
        print(f"超时设置: {timeout}秒")
        print(f"请求数据: {payload}")
        
        resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
        
        print(f"响应状态码: {resp.status_code}")
        
        if resp.status_code != 200:
            error_msg = f"生成失败 (HTTP {resp.status_code})"
            try:
                error_detail = resp.json()
                error_msg += f"\n{json.dumps(error_detail, indent=2, ensure_ascii=False)}"
            except:
                error_msg += f"\n{resp.text[:500]}"
            return error_msg, None
        
        resp.raise_for_status()
        result = resp.json()
        
        # 处理响应
        images = result.get("data", [])
        if not images:
            return f"响应无图像数据：{json.dumps(result, indent=2, ensure_ascii=False)}", None

        if "url" in images[0]:
            img_resp = requests.get(images[0]["url"], timeout=30)
            img_resp.raise_for_status()
            return "生成成功", Image.open(io.BytesIO(img_resp.content))

        if "b64_json" in images[0]:
            img_bytes = base64.b64decode(images[0]["b64_json"])
            return "生成成功", Image.open(io.BytesIO(img_bytes))

        return f"未知响应格式：{json.dumps(result, indent=2, ensure_ascii=False)}", None
        
    except requests.exceptions.Timeout:
        return f"请求超时（{timeout}秒），请增加超时时间或稍后重试", None
    except Exception as e:
        err_text = resp.text if 'resp' in locals() else ""
        return f"生成失败：{str(e)}\n{err_text}", None


# =============================================
# 尺寸管理函数
# =============================================
def parse_size_input(size_str):
    """解析尺寸输入，确保格式正确"""
    try:
        # 移除空格
        size_str = size_str.strip().replace(" ", "")
        
        # 检查是否是 "宽x高" 格式
        if "x" in size_str.lower():
            parts = size_str.lower().split("x")
            if len(parts) == 2:
                width = int(parts[0])
                height = int(parts[1])
                if width > 0 and height > 0:
                    return f"{width}x{height}"
        
        # 如果格式不正确，返回默认值
        return "1024x1024"
    except:
        return "1024x1024"

def add_custom_size(size_list, custom_size):
    """添加自定义尺寸到下拉列表"""
    parsed_size = parse_size_input(custom_size)
    if parsed_size and parsed_size not in size_list:
        # 创建新列表，将自定义尺寸添加到开头
        new_list = [parsed_size] + [s for s in size_list if s != parsed_size]
        return gr.update(choices=new_list, value=parsed_size)
    return gr.update()


# =============================================
# 异步任务管理函数
# =============================================
def edit_image_async(
    prompt,
    image=None,
    mask=None,
    model="LongCat-Image-Edit",
    size="1024x1024",
    response_format="b64_json",
    base_url="https://api.moark.com/v1",
    api_key="",
    timeout=60,
):
    """使用 /async/images/edits 接口进行异步图像编辑"""
    if not prompt.strip():
        return "请输入提示词", None, ""
    if not api_key.strip():
        return "请配置 API Key", None, ""
    if image is None:
        return "请上传要编辑的图像", None, ""

    url = f"{base_url.rstrip('/')}/async/images/edits"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
    }

    try:
        # 将 PIL Image 转换为 bytes
        img_buffer = io.BytesIO()
        image.save(img_buffer, format="PNG")
        img_bytes = img_buffer.getvalue()
        
        # 准备 multipart/form-data
        files = {
            'image': ('image.png', img_bytes, 'image/png'),
        }
        
        # 如果有 mask 图像
        if mask is not None:
            mask_buffer = io.BytesIO()
            mask.save(mask_buffer, format="PNG")
            files['mask'] = ('mask.png', mask_buffer.getvalue(), 'image/png')
        
        # 准备表单数据 (参考 curl 测试，所有字段都提供)
        data = {
            'model': model,
            'prompt': prompt.strip(),
            'mask': '',
            'size': size,
            'user': '',
            'n': '1',
            'response_format': response_format,
        }
            
        print(f"[异步编辑] 请求 URL: {url}")
        print(f"[异步编辑] 使用模型：{model}")
        print(f"[异步编辑] 输出尺寸：{size}")
        print(f"[异步编辑] 表单数据：{data}")
        
        # 发送请求
        resp = requests.post(
            url, 
            files=files, 
            data=data, 
            headers=headers, 
            timeout=timeout
        )
        
        print(f"[异步编辑] 响应状态码：{resp.status_code}")
        
        if resp.status_code != 200:
            error_msg = f"提交失败 (HTTP {resp.status_code})"
            try:
                error_detail = resp.json()
                error_msg += f"\n{json.dumps(error_detail, indent=2, ensure_ascii=False)}"
            except:
                error_msg += f"\n{resp.text[:500]}"
            print(f"[异步编辑] 错误：{error_msg}")
            return error_msg, None, ""
        
        resp.raise_for_status()
        result = resp.json()
        print(f"[异步编辑] 响应结果：{json.dumps(result, ensure_ascii=False, indent=2)}")
        
        # 解析异步响应
        task_id = result.get("task_id", "")
        if not task_id:
            err_msg = f"响应无 task_id: {json.dumps(result, indent=2, ensure_ascii=False)}"
            print(f"[异步编辑] {err_msg}")
            return err_msg, None, ""
        
        status = result.get("status", "unknown")
        success_msg = f"✅ 任务已提交成功！\n📝 Task ID: {task_id}\n📊 状态：{status}"
        print(f"[异步编辑] {success_msg}")
        return success_msg, None, task_id
        
    except requests.exceptions.Timeout:
        err_msg = f"请求超时（{timeout}秒）"
        print(f"[异步编辑] {err_msg}")
        return err_msg, None, ""
    except Exception as e:
        err_msg = f"提交失败：{str(e)}"
        print(f"[异步编辑] {err_msg}")
        return err_msg, None, ""


def query_async_task(task_id, base_url="https://api.moark.com/v1", api_key="", timeout=30):
    """查询异步任务状态"""
    if not task_id:
        return "请提供 Task ID", None, "no_task"
    if not api_key.strip():
        return "请配置 API Key", None, "error"

    # 使用响应中返回的 URL 格式：https://moark.com/api/v1/task/{task_id}
    url = f"https://moark.com/api/v1/task/{task_id}"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
    }

    try:
        print(f"[查询任务] 查询 URL: {url}")
        resp = requests.get(url, headers=headers, timeout=timeout)
        
        print(f"[查询任务] 响应状态码：{resp.status_code}")
        
        if resp.status_code != 200:
            error_msg = f"查询失败 (HTTP {resp.status_code})"
            try:
                error_detail = resp.json()
                error_msg += f"\n{json.dumps(error_detail, indent=2, ensure_ascii=False)}"
            except:
                error_msg += f"\n{resp.text[:500]}"
            print(f"[查询任务] 错误：{error_msg}")
            return error_msg, None, "error"
        
        resp.raise_for_status()
        result = resp.json()
        print(f"[查询任务] 响应结果：{json.dumps(result, ensure_ascii=False, indent=2)}")
        
        # 解析响应
        status = result.get("status", "unknown")
        created_at = result.get("created_at", "")
        started_at = result.get("started_at", "")
        completed_at = result.get("completed_at", "")
        
        status_msg = f"📊 任务状态：{status}"
        if created_at:
            # 转换时间戳为可读格式 (如果是数字)
            if isinstance(created_at, (int, float)):
                from datetime import datetime
                created_at = datetime.fromtimestamp(created_at / 1000).strftime('%Y-%m-%d %H:%M:%S')
            status_msg += f"\n⏰ 创建时间：{created_at}"
        if started_at:
            if isinstance(started_at, (int, float)):
                from datetime import datetime
                started_at = datetime.fromtimestamp(started_at / 1000).strftime('%Y-%m-%d %H:%M:%S')
            status_msg += f"\n🚀 开始时间：{started_at}"
        if completed_at:
            if isinstance(completed_at, (int, float)):
                from datetime import datetime
                completed_at = datetime.fromtimestamp(completed_at / 1000).strftime('%Y-%m-%d %H:%M:%S')
            status_msg += f"\n✅ 完成时间：{completed_at}"
        
        # 如果任务成功，处理图像
        if status == "success":
            output = result.get("output", {})
            if output:
                # 处理 b64_json 格式
                if "b64_json" in output:
                    img_bytes = base64.b64decode(output["b64_json"])
                    # 检测是否为视频
                    if img_bytes[:4] == b'\x00\x00\x00' or img_bytes[:4] == b'ftyp':
                        return f"{status_msg}\n\n✅ 处理成功 (视频需要下载)", None, "success"
                    return f"{status_msg}\n\n✅ 处理成功", Image.open(io.BytesIO(img_bytes)), "success"
                
                # 处理 url 格式
                elif "url" in output:
                    img_resp = requests.get(output["url"], timeout=30)
                    img_resp.raise_for_status()
                    # 检测是视频还是图像
                    content_type = img_resp.headers.get("Content-Type", "")
                    url = output["url"].lower()
                    if "video" in content_type or any(url.endswith(ext) for ext in ('.mp4', '.webm', '.mov', '.avi')):
                        return f"{status_msg}\n\n✅ 处理成功\n🔗 {output['url']}", None, "success"
                    return f"{status_msg}\n\n✅ 处理成功", Image.open(io.BytesIO(img_resp.content)), "success"
                
                # 处理 file_url 格式
                elif "file_url" in output:
                    file_url = output["file_url"]
                    print(f"[查询任务] 获取到 file_url: {file_url}")
                    img_resp = requests.get(file_url, timeout=30)
                    img_resp.raise_for_status()
                    # 更新数据库中的 file_url
                    update_task_status(task_id, "success", result={"file_url": file_url}, file_url=file_url)
                    
                    # 检测是视频还是图像
                    content_type = img_resp.headers.get("Content-Type", "")
                    if "video" in content_type or file_url.lower().endswith(('.mp4', '.webm', '.mov', '.avi')):
                        return f"{status_msg}\n\n✅ 处理成功\n🔗 {file_url}", None, "success"
                    
                    return f"{status_msg}\n\n✅ 处理成功\n🔗 {file_url}", Image.open(io.BytesIO(img_resp.content)), "success"
            
            return f"{status_msg}\n\n⚠️ 但无图像数据", None, "success"
        
        elif status == "failure":
            error_info = result.get("error", "未知错误")
            return f"{status_msg}\n\n❌ 错误：{error_info}", None, "failure"
        
        elif status == "cancelled":
            return f"{status_msg}\n\n❌ 任务已取消", None, "cancelled"
        
        else:
            # waiting 或 in_progress
            return f"{status_msg}\n\n⏳ 请耐心等待...", None, "pending"
        
    except requests.exceptions.Timeout:
        err_msg = f"查询超时（{timeout}秒）"
        print(f"[查询任务] {err_msg}")
        return err_msg, None, "timeout"
    except Exception as e:
        err_msg = f"查询失败：{str(e)}"
        print(f"[查询任务] {err_msg}")
        return err_msg, None, "error"


def query_video_async_task(task_id, base_url="https://api.moark.com/v1", api_key="", timeout=30):
    """查询异步视频任务状态"""
    if not task_id:
        return "请提供 Task ID", None
    if not api_key.strip():
        return "请配置 API Key", None

    url = f"https://moark.com/api/v1/task/{task_id}"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
    }

    try:
        print(f"[查询视频任务] 查询 URL: {url}")
        resp = requests.get(url, headers=headers, timeout=timeout)
        
        print(f"[查询视频任务] 响应状态码：{resp.status_code}")
        
        if resp.status_code != 200:
            error_msg = f"查询失败 (HTTP {resp.status_code})"
            try:
                error_detail = resp.json()
                error_msg += f"\n{json.dumps(error_detail, indent=2, ensure_ascii=False)}"
            except:
                error_msg += f"\n{resp.text[:500]}"
            print(f"[查询视频任务] 错误：{error_msg}")
            return error_msg, None
        
        resp.raise_for_status()
        result = resp.json()
        print(f"[查询视频任务] 响应结果：{json.dumps(result, ensure_ascii=False, indent=2)}")
        
        status = result.get("status", "unknown")
        created_at = result.get("created_at", "")
        started_at = result.get("started_at", "")
        completed_at = result.get("completed_at", "")
        
        status_msg = f"📊 任务状态：{status}"
        if created_at:
            if isinstance(created_at, (int, float)):
                from datetime import datetime
                created_at = datetime.fromtimestamp(created_at / 1000).strftime('%Y-%m-%d %H:%M:%S')
            status_msg += f"\n⏰ 创建时间：{created_at}"
        if started_at:
            if isinstance(started_at, (int, float)):
                from datetime import datetime
                started_at = datetime.fromtimestamp(started_at / 1000).strftime('%Y-%m-%d %H:%M:%S')
            status_msg += f"\n🚀 开始时间：{started_at}"
        if completed_at:
            if isinstance(completed_at, (int, float)):
                from datetime import datetime
                completed_at = datetime.fromtimestamp(completed_at / 1000).strftime('%Y-%m-%d %H:%M:%S')
            status_msg += f"\n✅ 完成时间：{completed_at}"
        
        if status == "success":
            output = result.get("output", {})
            if output:
                if "url" in output:
                    video_url = output["url"]
                    print(f"[查询视频任务] 获取到视频 URL: {video_url}")
                    return f"{status_msg}\n\n✅ 处理成功\n🔗 {video_url}", video_url, "success"
                
                elif "file_url" in output:
                    file_url = output["file_url"]
                    print(f"[查询视频任务] 获取到 file_url: {file_url}")
                    return f"{status_msg}\n\n✅ 处理成功\n🔗 {file_url}", file_url, "success"
            
            return f"{status_msg}\n\n⚠️ 但无视频数据", None, "success"
        
        elif status == "failure":
            error_info = result.get("error", "未知错误")
            return f"{status_msg}\n\n❌ 错误：{error_info}", None, "failure"
        
        elif status == "cancelled":
            return f"{status_msg}\n\n❌ 任务已取消", None, "cancelled"
        
        else:
            return f"{status_msg}\n\n⏳ 请耐心等待...", None, "pending"
        
    except requests.exceptions.Timeout:
        err_msg = f"查询超时（{timeout}秒）"
        print(f"[查询视频任务] {err_msg}")
        return err_msg, None, "failure"
    except Exception as e:
        err_msg = f"查询失败：{str(e)}"
        print(f"[查询视频任务] {err_msg}")
        return err_msg, None, "failure"


def generate_text_to_image_async(
    prompt,
    negative_prompt="",
    model="FLUX.1-dev",
    size="1024x1024",
    base_url="https://api.moark.com/v1",
    api_key="",
    timeout=60,
):
    """使用 /async/images/generations 接口进行异步文生图"""
    if not prompt.strip():
        return "请输入提示词", None, ""
    if not api_key.strip():
        return "请配置 API Key", None, ""

    url = f"{base_url.rstrip('/')}/async/images/generations"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "prompt": prompt.strip(),
        "size": size,
        "user": None,
        "n": 1,
        "response_format": "b64_json",
    }
    
    # 添加负提示词（如果提供）
    if negative_prompt and negative_prompt.strip():
        payload["negative_prompt"] = negative_prompt.strip()

    try:
        print(f"[异步文生图] 请求 URL: {url}")
        print(f"[异步文生图] 使用模型：{model}")
        print(f"[异步文生图] 输出尺寸：{size}")
        print(f"[异步文生图] 请求数据：{json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
        
        print(f"[异步文生图] 响应状态码：{resp.status_code}")
        
        if resp.status_code != 200:
            error_msg = f"提交失败 (HTTP {resp.status_code})"
            try:
                error_detail = resp.json()
                error_msg += f"\n{json.dumps(error_detail, indent=2, ensure_ascii=False)}"
            except:
                error_msg += f"\n{resp.text[:500]}"
            print(f"[异步文生图] 错误：{error_msg}")
            return error_msg, None, ""
        
        resp.raise_for_status()
        result = resp.json()
        print(f"[异步文生图] 响应结果：{json.dumps(result, ensure_ascii=False, indent=2)}")
        
        # 解析异步响应
        task_id = result.get("task_id", "")
        if not task_id:
            err_msg = f"响应无 task_id: {json.dumps(result, indent=2, ensure_ascii=False)}"
            print(f"[异步文生图] {err_msg}")
            return err_msg, None, ""
        
        status = result.get("status", "unknown")
        success_msg = f"✅ 任务已提交成功！\n📝 Task ID: {task_id}\n📊 状态：{status}"
        print(f"[异步文生图] {success_msg}")
        return success_msg, None, task_id
        
    except requests.exceptions.Timeout:
        err_msg = f"请求超时（{timeout}秒）"
        print(f"[异步文生图] {err_msg}")
        return err_msg, None, ""
    except Exception as e:
        err_msg = f"提交失败：{str(e)}"
        print(f"[异步文生图] {err_msg}")
        return err_msg, None, ""


# =============================================
# 异步文生视频函数
# =============================================
def generate_text_to_video_async(
    prompt,
    model="stepvideo-t2v",
    duration=5,
    base_url="https://api.moark.com/v1",
    api_key="",
    timeout=60,
):
    """使用 /async/videos/generations 接口进行异步文生视频"""
    if not prompt.strip():
        return "请输入提示词", None, ""
    if not api_key.strip():
        return "请配置 API Key", None, ""

    url = f"{base_url.rstrip('/')}/async/videos/generations"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "prompt": prompt.strip(),
        "duration": duration,
        "mode": "image-to-video",
    }

    try:
        print(f"[异步文生视频] 请求 URL: {url}")
        print(f"[异步文生视频] 使用模型：{model}")
        print(f"[异步文生视频] 请求数据：{json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
        
        print(f"[异步文生视频] 响应状态码：{resp.status_code}")
        
        if resp.status_code != 200:
            error_msg = f"提交失败 (HTTP {resp.status_code})"
            try:
                error_detail = resp.json()
                error_msg += f"\n{json.dumps(error_detail, indent=2, ensure_ascii=False)}"
            except:
                error_msg += f"\n{resp.text[:500]}"
            print(f"[异步文生视频] 错误：{error_msg}")
            return error_msg, None, ""
        
        resp.raise_for_status()
        result = resp.json()
        print(f"[异步文生视频] 响应结果：{json.dumps(result, ensure_ascii=False, indent=2)}")
        
        task_id = result.get("task_id", "")
        if not task_id:
            err_msg = f"响应无 task_id: {json.dumps(result, indent=2, ensure_ascii=False)}"
            print(f"[异步文生视频] {err_msg}")
            return err_msg, None, ""
        
        status = result.get("status", "unknown")
        success_msg = f"✅ 视频任务已提交成功！\n📝 Task ID: {task_id}\n📊 状态：{status}"
        print(f"[异步文生视频] {success_msg}")
        return success_msg, None, task_id
        
    except requests.exceptions.Timeout:
        err_msg = f"请求超时（{timeout}秒）"
        print(f"[异步文生视频] {err_msg}")
        return err_msg, None, ""
    except Exception as e:
        err_msg = f"提交失败：{str(e)}"
        print(f"[异步文生视频] {err_msg}")
        return err_msg, None, ""


# =============================================
# 异步图生视频函数
# =============================================
def generate_image_to_video_async(
    prompt,
    image_url="",
    model="LTX-2",
    duration=5,
    base_url="https://api.moark.com/v1",
    api_key="",
    timeout=60,
):
    """使用 /async/videos/image-to-video 接口进行异步图生视频"""
    if not prompt.strip() and not image_url.strip():
        return "请输入提示词或上传图片", None, ""
    if not api_key.strip():
        return "请配置 API Key", None, ""

    url = f"{base_url.rstrip('/')}/async/videos/image-to-video"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "prompt": prompt.strip(),
        "duration": duration,
    }
    
    if image_url.strip():
        payload["image_url"] = image_url.strip()

    try:
        print(f"[异步图生视频] 请求 URL: {url}")
        print(f"[异步图生视频] 使用模型：{model}")
        print(f"[异步图生视频] 请求数据：{json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
        
        print(f"[异步图生视频] 响应状态码：{resp.status_code}")
        
        if resp.status_code != 200:
            error_msg = f"提交失败 (HTTP {resp.status_code})"
            try:
                error_detail = resp.json()
                error_msg += f"\n{json.dumps(error_detail, indent=2, ensure_ascii=False)}"
            except:
                error_msg += f"\n{resp.text[:500]}"
            print(f"[异步图生视频] 错误：{error_msg}")
            return error_msg, None, ""
        
        resp.raise_for_status()
        result = resp.json()
        print(f"[异步图生视频] 响应结果：{json.dumps(result, ensure_ascii=False, indent=2)}")
        
        task_id = result.get("task_id", "")
        if not task_id:
            err_msg = f"响应无 task_id: {json.dumps(result, indent=2, ensure_ascii=False)}"
            print(f"[异步图生视频] {err_msg}")
            return err_msg, None, ""
        
        status = result.get("status", "unknown")
        success_msg = f"✅ 视频任务已提交成功！\n📝 Task ID: {task_id}\n📊 状态：{status}"
        print(f"[异步图生视频] {success_msg}")
        return success_msg, None, task_id
        
    except requests.exceptions.Timeout:
        err_msg = f"请求超时（{timeout}秒）"
        print(f"[异步图生视频] {err_msg}")
        return err_msg, None, ""
    except Exception as e:
        err_msg = f"提交失败：{str(e)}"
        print(f"[异步图生视频] {err_msg}")
        return err_msg, None, ""


# =============================================
# Gradio 界面
# =============================================
css = """
.warning {
    color: #d32f2f;
    font-weight: bold;
    margin: 12px 0;
    padding: 12px;
    background: #ffebee;
    border-radius: 8px;
    border-left: 4px solid #f44336;
}
.success {
    color: #2e7d32;
    font-weight: bold;
    margin: 12px 0;
    padding: 12px;
    background: #e8f5e8;
    border-radius: 8px;
    border-left: 4px solid #4caf50;
}
.info {
    color: #0b5e8a;
    margin: 8px 0;
    padding: 8px;
    background: #e3f2fd;
    border-radius: 4px;
    border-left: 4px solid #2196f3;
}
.model-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: bold;
    margin-left: 8px;
}
.model-turbo {
    background: #fff3e0;
    color: #e65100;
}
.model-edit {
    background: #e8eaf6;
    color: #1a237e;
}
.timeout-note {
    font-size: 12px;
    color: #666;
    margin-top: 4px;
}
.size-input-row {
    margin-top: 8px;
    margin-bottom: 8px;
}
.custom-size-note {
    font-size: 11px;
    color: #888;
    font-style: italic;
}
.author-footer {
    text-align: center;
    padding: 20px;
    margin-top: 30px;
    border-top: 2px solid #e0e0e0;
    background: #f8f9fa;
    border-radius: 8px;
}
.author-footer a {
    color: #667eea;
    text-decoration: none;
    font-weight: bold;
}
.author-footer a:hover {
    color: #764ba2;
    text-decoration: underline;
}
"""

with gr.Blocks(title="白嫖大师 - 图像视频生成工具", css=css) as demo:
    config_state = gr.State(load_config())
    
    # 顶部标题和作者信息（始终显示）
    gr.Markdown("""
    <div style="text-align: center; padding: 15px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <h1 style="color: white; margin: 10px 0; font-size: 28px;">🎨 白嫖大师 - 图像视频生成工具</h1>
        <p style="color: white; font-size: 16px; margin: 10px 0;">
            <strong>👨‍💻 作者：你们喜爱的老王</strong>
        </p>
        <p style="color: #ffd700; font-size: 14px; margin: 5px 0;">
            <a href="https://space.bilibili.com/97727630" target="_blank" style="color: #ffd700; text-decoration: none; margin: 0 10px;">
                🎬 B站主页
            </a> | 
            <a href="https://github.com/ops120/bai-piao-master" target="_blank" style="color: #ffd700; text-decoration: none; margin: 0 10px;">
                ⭐ GitHub项目
            </a>
        </p>
        <p style="color: #e0e0e0; font-size: 13px; margin: 10px 0;">
            聚合免费AI，创意不限量 | 零成本玩转AI图像生成
        </p>
    </div>
    """)

    # 配置页
    with gr.Column(visible=True) as config_col:
        gr.Markdown("### ⚙️ 配置（保存到 moark_config.json）")
        base_url_in = gr.Textbox(
            label="Base URL", 
            value=config_state.value["base_url"],
            info="例如：https://api.moark.com/v1"
        )
        api_key_in = gr.Textbox(
            label="API Key", 
            type="password", 
            value=config_state.value["api_key"],
            info="你的 Moark API 密钥"
        )
        
        with gr.Row():
            with gr.Column():
                text2img_model_in = gr.Textbox(
                    label="文生图默认模型", 
                    value=config_state.value["text2img_model"],
                    info="例如：z-image-turbo"
                )
            with gr.Column():
                edit_model_in = gr.Textbox(
                    label="图生图/编辑默认模型", 
                    value=config_state.value["edit_model"],
                    info="例如：Qwen-Image-Edit"
                )
        
        # 异步模型配置
        gr.Markdown("#### ⏳ 异步模型配置")
        with gr.Row():
            with gr.Column():
                async_txt2img_models_in = gr.Textbox(
                    label="异步文生图模型列表（用逗号分隔）", 
                    value=", ".join(config_state.value.get("async_txt2img_models", ["FLUX.1-dev"])),
                    info="例如：FLUX.1-dev, LongCat-Image, flux-1-schnell"
                )
            with gr.Column():
                async_edit_models_in = gr.Textbox(
                    label="异步编辑模型列表（用逗号分隔）", 
                    value=", ".join(config_state.value.get("async_edit_models", ["LongCat-Image-Edit"])),
                    info="例如：LongCat-Image-Edit, Qwen-Image-Edit-2511"
                )
        
        with gr.Row():
            with gr.Column():
                async_txt2vid_models_in = gr.Textbox(
                    label="异步文生视频模型列表（用逗号分隔）", 
                    value=", ".join(config_state.value.get("async_txt2vid_models", ["stepvideo-t2v"])),
                    info="例如：stepvideo-t2v"
                )
            with gr.Column():
                async_img2vid_models_in = gr.Textbox(
                    label="异步图生视频模型列表（用逗号分隔）", 
                    value=", ".join(config_state.value.get("async_img2vid_models", ["LTX-2"])),
                    info="例如：LTX-2"
                )
        
        # 尺寸配置
        with gr.Row():
            with gr.Column():
                default_size_in = gr.Textbox(
                    label="默认输出尺寸", 
                    value=config_state.value["default_size"],
                    info="例如：1024x1024"
                )
            with gr.Column():
                available_sizes_in = gr.Textbox(
                    label="可用尺寸列表（用逗号分隔）", 
                    value=", ".join(config_state.value["available_sizes"]),
                    info="例如：512x512, 768x768, 1024x1024"
                )
        
        # 超时配置
        timeout_in = gr.Number(
            label="请求超时时间（秒）", 
            value=config_state.value["timeout"],
            minimum=30,
            maximum=600,
            step=10,
            info="设置 API 请求的超时时间，复杂任务需要更长时间"
        )
        gr.Markdown(
            "💡 提示：如果生成复杂图像经常超时，可以适当增加超时时间",
            elem_classes="timeout-note"
        )
        
        save_btn = gr.Button("💾 保存并进入", variant="primary", size="lg")
        status_config = gr.Markdown("")

    # 主界面
    with gr.Column(visible=False) as main_col:
        gr.Markdown("## 🎨 图像视频生成工具")
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown(
                    """
                    ### 📝 功能说明
                    - **文生图**：纯文本生成图像
                    - **图像编辑**：上传图片进行编辑
                    - **URL参考图**：通过图片URL生成
                    
                    ⚡ **异步功能**：
                    - 提交任务后可关闭页面，任务会在后台处理
                    - 在「任务队列」中查看进度和结果
                    - 支持批量查询和批量下载
                    
                    ⏱️ 当前超时设置: {}秒
                    📏 默认尺寸: {}
                    """.format(
                        config_state.value.get("timeout", 180),
                        config_state.value.get("default_size", "1024x1024")
                    ),
                    elem_classes="info"
                )
            
            with gr.Column(scale=3):
                with gr.Tabs():
                    # ===== 文生图标签页 =====
                    with gr.TabItem("📝 文生图", id="txt2img_tab"):
                        gr.Markdown(
                            "### 文本生成图像",
                            elem_classes="success"
                        )
                        gr.Markdown(
                            "⚡ 默认模型: **z-image-turbo**",
                            elem_classes="model-badge model-turbo"
                        )
                        
                        with gr.Row():
                            with gr.Column():
                                prompt_txt = gr.Textbox(
                                    label="提示词", 
                                    lines=4,
                                    placeholder="例如: 一只可爱的猫咪，4k高清，写实风格",
                                    value="一只可爱的猫咪"
                                )
                                negative_txt = gr.Textbox(
                                    label="负提示词 (可选)", 
                                    lines=2,
                                    placeholder="例如: 模糊, 低质量, 水印"
                                )
                            
                            with gr.Column():
                                model_txt = gr.Textbox(
                                    label="模型 (可修改)", 
                                    value=lambda: config_state.value["text2img_model"]
                                )
                                
                                # 可修改的尺寸选择
                                with gr.Row(elem_classes="size-input-row"):
                                    size_txt = gr.Dropdown(
                                        choices=config_state.value["available_sizes"],
                                        value=lambda: config_state.value["default_size"],
                                        label="输出尺寸",
                                        allow_custom_value=True,  # 允许自定义输入
                                        info="可以选择预设或输入自定义尺寸 (例如: 1280x960)"
                                    )
                                
                                n_txt = gr.Slider(
                                    minimum=1, 
                                    maximum=4, 
                                    value=1, 
                                    step=1, 
                                    label="生成数量"
                                )
                                btn_txt = gr.Button("🚀 生成图像", variant="primary", size="lg")
                        
                        with gr.Row():
                            with gr.Column():
                                status_txt = gr.Textbox(
                                    label="状态", 
                                    interactive=False, 
                                    lines=4
                                )
                            with gr.Column():
                                out_txt = gr.Image(label="生成结果")
                    
                    # ===== 图像编辑标签页 =====
                    with gr.TabItem("✏️ 图像编辑", id="edit_tab"):
                        gr.Markdown(
                            "### 图生图 / 图像编辑",
                            elem_classes="success"
                        )
                        gr.Markdown(
                            "✏️ 默认模型: **Qwen-Image-Edit**",
                            elem_classes="model-badge model-edit"
                        )
                        
                        with gr.Row():
                            with gr.Column():
                                input_image = gr.Image(
                                    type="pil", 
                                    label="上传源图像 (PNG格式)",
                                    sources=["upload", "clipboard"],
                                    height=300
                                )
                                mask_image = gr.Image(
                                    type="pil", 
                                    label="蒙版图像 (可选，白色区域将被编辑)",
                                    sources=["upload", "clipboard"],
                                    height=300
                                )
                            
                            with gr.Column():
                                prompt_edit = gr.Textbox(
                                    label="编辑提示词", 
                                    lines=4,
                                    placeholder="例如: 黑丝, 性感风格, 高细节, 保持人物一致性",
                                    value="黑丝"
                                )
                                model_edit = gr.Textbox(
                                    label="模型 (可修改)", 
                                    value=lambda: config_state.value["edit_model"]
                                )
                                
                                # 可修改的尺寸选择
                                with gr.Row(elem_classes="size-input-row"):
                                    size_edit = gr.Dropdown(
                                        choices=config_state.value["available_sizes"],
                                        value=lambda: config_state.value["default_size"],
                                        label="输出尺寸",
                                        allow_custom_value=True,  # 允许自定义输入
                                        info="可以选择预设或输入自定义尺寸"
                                    )
                                
                                n_edit = gr.Slider(
                                    minimum=1, 
                                    maximum=4, 
                                    value=1, 
                                    step=1, 
                                    label="生成数量"
                                )
                                btn_edit = gr.Button("🚀 生成编辑图像", variant="primary", size="lg")
                        
                        with gr.Row():
                            with gr.Column():
                                status_edit = gr.Textbox(
                                    label="状态", 
                                    interactive=False, 
                                    lines=4
                                )
                            with gr.Column():
                                out_edit = gr.Image(label="编辑结果")
                    
                    # ===== URL参考图标签页 =====
                    with gr.TabItem("🔗 URL参考图", id="url_tab"):
                        gr.Markdown(
                            "### 通过图片URL生成",
                            elem_classes="info"
                        )
                        gr.Markdown(
                            "🔗 默认使用编辑模型: **Qwen-Image-Edit**",
                            elem_classes="model-badge model-edit"
                        )
                        
                        with gr.Row():
                            with gr.Column():
                                ref_url = gr.Textbox(
                                    label="参考图片 URL", 
                                    placeholder="https://example.com/image.png",
                                    info="图片的公开访问URL"
                                )
                                prompt_ref = gr.Textbox(
                                    label="提示词", 
                                    lines=4,
                                    placeholder="描述想要的修改",
                                    value="黑丝"
                                )
                                neg_ref = gr.Textbox(
                                    label="负提示词 (可选)", 
                                    lines=2
                                )
                            
                            with gr.Column():
                                model_ref = gr.Textbox(
                                    label="模型 (可修改)", 
                                    value=lambda: config_state.value["edit_model"]
                                )
                                
                                # 可修改的尺寸选择
                                with gr.Row(elem_classes="size-input-row"):
                                    size_ref = gr.Dropdown(
                                        choices=config_state.value["available_sizes"],
                                        value=lambda: config_state.value["default_size"],
                                        label="输出尺寸",
                                        allow_custom_value=True,  # 允许自定义输入
                                        info="可以选择预设或输入自定义尺寸"
                                    )
                                
                                n_ref = gr.Slider(
                                    minimum=1, 
                                    maximum=4, 
                                    value=1, 
                                    step=1, 
                                    label="生成数量"
                                )
                                btn_ref = gr.Button("🔄 生成", variant="primary", size="lg")
                        
                        with gr.Row():
                            with gr.Column():
                                status_ref = gr.Textbox(
                                    label="状态", 
                                    interactive=False, 
                                    lines=4
                                )
                            with gr.Column():
                                out_ref = gr.Image(label="生成结果")
                    
                    # ===== 异步文生图标签页 =====
                    with gr.TabItem("⏳异步文生图", id="async_txt2img_tab"):
                        gr.Markdown(
                            "### 异步文本生成图像",
                            elem_classes="success"
                        )
                        gr.Markdown(
                            "⚡ 优势：避免超时，适合复杂图像生成 | 📊 支持状态轮询",
                            elem_classes="info"
                        )
                        
                        with gr.Row():
                            with gr.Column():
                                async_prompt_txt = gr.Textbox(
                                    label="提示词", 
                                    lines=4,
                                    placeholder="例如：一只可爱的猫咪，4k 高清，写实风格",
                                    value="一只可爱的猫咪"
                                )
                                async_negative_txt = gr.Textbox(
                                    label="负提示词 (可选)", 
                                    lines=2,
                                    placeholder="例如：模糊，低质量，水印"
                                )
                                # 异步文生图模型选择
                                async_model_txt = gr.Dropdown(
                                    label="模型 (可手动输入)", 
                                    choices=config_state.value.get("async_txt2img_models", ["FLUX.1-dev"]),
                                    value="FLUX.1-dev",
                                    allow_custom_value=True,
                                    info="选择预设模型或手动输入模型名称"
                                )
                                
                                with gr.Row(elem_classes="size-input-row"):
                                    async_size_txt = gr.Dropdown(
                                        choices=config_state.value["available_sizes"],
                                        value=lambda: config_state.value["default_size"],
                                        label="输出尺寸",
                                        allow_custom_value=True,
                                        info="可以选择预设或输入自定义尺寸"
                                    )
                                
                                async_submit_btn = gr.Button("📤 提交异步任务", variant="primary", size="lg")
                            
                            with gr.Column():
                                async_task_id_txt = gr.Textbox(
                                    label="Task ID", 
                                    interactive=False,
                                    placeholder="提交后自动填充",
                                    lines=1
                                )
                                async_status_txt = gr.Textbox(
                                    label="提交状态", 
                                    interactive=False, 
                                    lines=4
                                )
                        
                        gr.Markdown("---")
                        
                        with gr.Row():
                            with gr.Column():
                                query_task_id = gr.Textbox(
                                    label="查询 Task ID",
                                    placeholder="输入或粘贴 Task ID 进行查询",
                                    lines=1
                                )
                                query_btn = gr.Button("🔍 查询任务状态", variant="secondary")
                                refresh_btn = gr.Button("🔄 刷新状态", variant="secondary")
                            
                            with gr.Column():
                                async_result_status = gr.Textbox(
                                    label="任务状态", 
                                    interactive=False, 
                                    lines=6
                                )
                            with gr.Column():
                                async_result_img = gr.Image(label="生成结果")
                    
                    # ===== 异步图像编辑标签页 =====
                    with gr.TabItem("⏳异步编辑", id="async_edit_tab"):
                        gr.Markdown(
                            "### 异步图像编辑",
                            elem_classes="success"
                        )
                        gr.Markdown(
                            "⚡ 优势：避免超时，适合复杂编辑任务 | 📊 支持状态轮询",
                            elem_classes="info"
                        )
                        
                        with gr.Row():
                            with gr.Column():
                                async_input_image = gr.Image(
                                    type="pil", 
                                    label="上传源图像 (PNG 格式)",
                                    sources=["upload", "clipboard"],
                                    height=250
                                )
                                async_mask_image = gr.Image(
                                    type="pil", 
                                    label="蒙版图像 (可选，白色区域将被编辑)",
                                    sources=["upload", "clipboard"],
                                    height=250
                                )
                            
                            with gr.Column():
                                async_prompt_edit = gr.Textbox(
                                    label="编辑提示词", 
                                    lines=4,
                                    placeholder="例如：黑丝，性感风格，高细节，保持人物一致性",
                                    value="黑丝"
                                )
                                # 异步编辑模型选择
                                async_model_edit = gr.Dropdown(
                                    label="模型 (可手动输入)", 
                                    choices=config_state.value.get("async_edit_models", ["LongCat-Image-Edit"]),
                                    value="LongCat-Image-Edit",
                                    allow_custom_value=True,
                                    info="选择预设模型或手动输入模型名称"
                                )
                                
                                with gr.Row(elem_classes="size-input-row"):
                                    async_size_edit = gr.Dropdown(
                                        choices=config_state.value["available_sizes"],
                                        value=lambda: config_state.value["default_size"],
                                        label="输出尺寸",
                                        allow_custom_value=True,
                                        info="可以选择预设或输入自定义尺寸"
                                    )
                                
                                async_edit_submit_btn = gr.Button("📤 提交异步任务", variant="primary", size="lg")
                        
                        with gr.Row():
                            with gr.Column():
                                async_edit_task_id_txt = gr.Textbox(
                                    label="Task ID", 
                                    interactive=False,
                                    placeholder="提交后自动填充",
                                    lines=1
                                )
                                async_edit_status_txt = gr.Textbox(
                                    label="提交状态", 
                                    interactive=False, 
                                    lines=4
                                )
                        
                        gr.Markdown("---")
                        
                        with gr.Row():
                            with gr.Column():
                                async_edit_query_task_id = gr.Textbox(
                                    label="查询 Task ID",
                                    placeholder="输入或粘贴 Task ID 进行查询",
                                    lines=1
                                )
                                async_edit_query_btn = gr.Button("🔍 查询任务状态", variant="secondary")
                                async_edit_refresh_btn = gr.Button("🔄 刷新状态", variant="secondary")
                            
                            with gr.Column():
                                async_edit_result_status = gr.Textbox(
                                    label="任务状态", 
                                    interactive=False, 
                                    lines=6
                                )
                            with gr.Column():
                                async_edit_result_img = gr.Image(label="编辑结果")
                    
                    # ===== 异步文生视频标签页 =====
                    with gr.TabItem("🎬 异步文生视频", id="async_txt2vid_tab"):
                        gr.Markdown(
                            "### 🎬 异步文生视频",
                            elem_classes="success"
                        )
                        gr.Markdown(
                            "⚡ 优势：文字生成视频 | 📊 支持状态轮询",
                            elem_classes="info"
                        )
                        
                        with gr.Row():
                            with gr.Column():
                                async_txt2vid_prompt = gr.Textbox(
                                    label="视频提示词", 
                                    lines=4,
                                    placeholder="例如：一只小猫在跳拉丁",
                                    value=""
                                )
                                async_txt2vid_model = gr.Dropdown(
                                    label="模型", 
                                    choices=config_state.value.get("async_txt2vid_models", ["stepvideo-t2v"]),
                                    value="stepvideo-t2v",
                                    allow_custom_value=True,
                                    info="选择视频生成模型"
                                )
                                async_txt2vid_submit_btn = gr.Button("📤 提交异步任务", variant="primary", size="lg")
                        
                        with gr.Row():
                            with gr.Column():
                                async_txt2vid_task_id_txt = gr.Textbox(
                                    label="Task ID", 
                                    interactive=False,
                                    placeholder="提交后自动填充",
                                    lines=1
                                )
                                async_txt2vid_status_txt = gr.Textbox(
                                    label="提交状态", 
                                    interactive=False, 
                                    lines=4
                                )
                        
                        gr.Markdown("---")
                        
                        with gr.Row():
                            with gr.Column():
                                async_txt2vid_query_task_id = gr.Textbox(
                                    label="查询 Task ID",
                                    placeholder="输入或粘贴 Task ID 进行查询",
                                    lines=1
                                )
                                async_txt2vid_query_btn = gr.Button("🔍 查询任务状态", variant="secondary")
                                async_txt2vid_refresh_btn = gr.Button("🔄 刷新状态", variant="secondary")
                            
                            with gr.Column():
                                async_txt2vid_result_status = gr.Textbox(
                                    label="任务状态", 
                                    interactive=False, 
                                    lines=6
                                )
                            with gr.Column():
                                async_txt2vid_result_video = gr.Video(label="视频结果")
                    
                    # ===== 异步图生视频标签页 =====
                    with gr.TabItem("🎥 异步图生视频", id="async_img2vid_tab"):
                        gr.Markdown(
                            "### 🎥 异步图生视频",
                            elem_classes="success"
                        )
                        gr.Markdown(
                            "⚡ 优势：图片生成视频 | 📊 支持状态轮询",
                            elem_classes="info"
                        )
                        
                        with gr.Row():
                            with gr.Column():
                                async_img2vid_input_image = gr.Image(
                                    type="pil", 
                                    label="上传源图像 (PNG 格式)",
                                    sources=["upload", "clipboard"],
                                    height=250
                                )
                                async_img2vid_prompt = gr.Textbox(
                                    label="视频提示词 (可选)", 
                                    lines=4,
                                    placeholder="描述视频应该如何运动",
                                    value=""
                                )
                                async_img2vid_model = gr.Dropdown(
                                    label="模型", 
                                    choices=config_state.value.get("async_img2vid_models", ["LTX-2"]),
                                    value="LTX-2",
                                    allow_custom_value=True,
                                    info="选择视频生成模型"
                                )
                                async_img2vid_submit_btn = gr.Button("📤 提交异步任务", variant="primary", size="lg")
                        
                        with gr.Row():
                            with gr.Column():
                                async_img2vid_task_id_txt = gr.Textbox(
                                    label="Task ID", 
                                    interactive=False,
                                    placeholder="提交后自动填充",
                                    lines=1
                                )
                                async_img2vid_status_txt = gr.Textbox(
                                    label="提交状态", 
                                    interactive=False, 
                                    lines=4
                                )
                        
                        gr.Markdown("---")
                        
                        with gr.Row():
                            with gr.Column():
                                async_img2vid_query_task_id = gr.Textbox(
                                    label="查询 Task ID",
                                    placeholder="输入或粘贴 Task ID 进行查询",
                                    lines=1
                                )
                                async_img2vid_query_btn = gr.Button("🔍 查询任务状态", variant="secondary")
                                async_img2vid_refresh_btn = gr.Button("🔄 刷新状态", variant="secondary")
                            
                            with gr.Column():
                                async_img2vid_result_status = gr.Textbox(
                                    label="任务状态", 
                                    interactive=False, 
                                    lines=6
                                )
                            with gr.Column():
                                async_img2vid_result_video = gr.Video(label="视频结果")
                    
                    # ===== 任务队列管理标签页 =====
                    with gr.TabItem("📋 任务队列", id="task_queue_tab"):
                        gr.Markdown(
                            "### 📋 任务队列管理",
                            elem_classes="success"
                        )
                        gr.Markdown(
                            "📅 按日期和类型筛选历史任务 | 🔄 批量查询任务状态 | 📊 查看任务详情",
                            elem_classes="info"
                        )
                        
                        with gr.Row():
                            with gr.Column(scale=1):
                                # 筛选条件
                                filter_date = gr.Dropdown(
                                    label="📅 选择日期",
                                    choices=[],
                                    value=None,
                                    allow_custom_value=True,
                                    info="选择要查看的日期"
                                )
                                filter_type = gr.Dropdown(
                                    label="📝 任务类型",
                                    choices=[
                                        ("全部", "all"),
                                        ("文生图", "async_txt2img"),
                                        ("图像编辑", "async_edit"),
                                        ("文生视频", "async_txt2vid"),
                                        ("图生视频", "async_img2vid")
                                    ],
                                    value="all",
                                    info="选择任务类型"
                                )
                                refresh_history_btn = gr.Button("🔄 刷新列表", variant="secondary")
                            
                            with gr.Column(scale=3):
                                # 任务列表
                                task_list = gr.Dataframe(
                                    headers=["Task ID", "类型", "状态", "提示词", "模型", "时间"],
                                    datatype=["str", "str", "str", "str", "str", "str"],
                                    label="任务列表",
                                    interactive=False,
                                    row_count=10
                                )
                        
                        gr.Markdown("---")
                        
                        with gr.Row():
                            with gr.Column():
                                with gr.Row():
                                    select_all_btn = gr.Button("✅ 全选", variant="secondary", size="sm")
                                    select_none_btn = gr.Button("❌ 取消全选", variant="secondary", size="sm")
                                    select_inverse_btn = gr.Button("🔄 反选", variant="secondary", size="sm")
                                
                                with gr.Row():
                                    batch_query_btn = gr.Button("🔍 批量查询选中任务", variant="primary")
                                    batch_download_btn = gr.Button("📥 批量下载选中任务", variant="primary")
                                
                                clear_history_btn = gr.Button("🗑️ 清空历史记录", variant="stop")
                            
                            with gr.Column():
                                selected_task_ids = gr.Textbox(
                                    label="选中的 Task ID 列表 (用逗号分隔)",
                                    interactive=False,
                                    lines=2
                                )
                        
                        with gr.Row():
                            with gr.Column():
                                task_detail_status = gr.Textbox(
                                    label="任务详情",
                                    interactive=False,
                                    lines=8
                                )
                            with gr.Column():
                                task_detail_img = gr.Image(label="图片结果")
                                task_detail_video = gr.Video(label="视频结果")
        
        back_btn = gr.Button("← 返回配置", variant="secondary")

    # ===== 事件绑定 =====
    def save_cfg(bu, key, txt_mdl, edit_mdl, default_size, available_sizes_str, timeout_val, 
                 async_txt2img_models_str, async_edit_models_str,
                 async_txt2vid_models_str, async_img2vid_models_str):
        # 解析可用尺寸列表
        available_list = [s.strip() for s in available_sizes_str.split(",") if s.strip()]
        if not available_list:
            available_list = DEFAULT_CONFIG["available_sizes"]
        
        # 确保默认尺寸在可用列表中
        default_size = default_size.strip()
        if default_size and default_size not in available_list:
            available_list.insert(0, default_size)
        
        # 解析异步模型列表
        async_txt2img_list = [m.strip() for m in async_txt2img_models_str.split(",") if m.strip()]
        if not async_txt2img_list:
            async_txt2img_list = DEFAULT_CONFIG["async_txt2img_models"]
        
        async_edit_list = [m.strip() for m in async_edit_models_str.split(",") if m.strip()]
        if not async_edit_list:
            async_edit_list = DEFAULT_CONFIG["async_edit_models"]
        
        async_txt2vid_list = [m.strip() for m in async_txt2vid_models_str.split(",") if m.strip()]
        if not async_txt2vid_list:
            async_txt2vid_list = DEFAULT_CONFIG["async_txt2vid_models"]
        
        async_img2vid_list = [m.strip() for m in async_img2vid_models_str.split(",") if m.strip()]
        if not async_img2vid_list:
            async_img2vid_list = DEFAULT_CONFIG["async_img2vid_models"]
        
        cfg = {
            "base_url": bu.strip().rstrip("/"),
            "api_key": key.strip(),
            "text2img_model": txt_mdl.strip() or "z-image-turbo",
            "edit_model": edit_mdl.strip() or "Qwen-Image-Edit",
            "default_size": default_size or "1024x1024",
            "available_sizes": available_list,
            "timeout": int(timeout_val) if timeout_val else 180,
            "async_txt2img_models": async_txt2img_list,
            "async_edit_models": async_edit_list,
            "async_txt2vid_models": async_txt2vid_list,
            "async_img2vid_models": async_img2vid_list
        }
        save_config(cfg)
        
        # 更新所有下拉框的选项
        return (
            cfg, 
            gr.update(visible=False), 
            gr.update(visible=True), 
            "✅ **配置已保存**",
            gr.update(choices=async_txt2img_list),
            gr.update(choices=async_edit_list),
            gr.update(choices=async_txt2vid_list),
            gr.update(choices=async_img2vid_list),
            gr.update(choices=available_list, value=default_size),
            gr.update(choices=available_list, value=default_size)
        )

    save_btn.click(
        save_cfg,
        inputs=[base_url_in, api_key_in, text2img_model_in, edit_model_in, 
                default_size_in, available_sizes_in, timeout_in,
                async_txt2img_models_in, async_edit_models_in,
                async_txt2vid_models_in, async_img2vid_models_in],
        outputs=[config_state, config_col, main_col, status_config,
                  async_model_txt, async_model_edit, async_txt2vid_model, async_img2vid_model,
                  async_size_edit, async_size_txt]
    )

    back_btn.click(
        lambda: (gr.update(visible=True), gr.update(visible=False)),
        outputs=[config_col, main_col]
    )

    # 文生图功能
    def do_txt2img(p, neg, mdl, sz, n, cfg):
        # 确保尺寸格式正确
        valid_size = parse_size_input(sz)
        return generate_text_to_image(
            prompt=p,
            negative_prompt=neg,
            model=mdl,
            size=valid_size,
            n=n,
            base_url=cfg["base_url"],
            api_key=cfg["api_key"],
            timeout=cfg.get("timeout", 180)
        )

    btn_txt.click(
        do_txt2img,
        inputs=[prompt_txt, negative_txt, model_txt, size_txt, n_txt, config_state],
        outputs=[status_txt, out_txt]
    )

    # 编辑功能
    def do_edit(img, mask, p, mdl, sz, n, cfg):
        if img is None:
            return "请上传源图像", None
        valid_size = parse_size_input(sz)
        return edit_image(
            prompt=p,
            image=img,
            mask=mask,
            model=mdl,
            n=n,
            size=valid_size,
            base_url=cfg["base_url"],
            api_key=cfg["api_key"],
            timeout=cfg.get("timeout", 180)
        )

    btn_edit.click(
        do_edit,
        inputs=[input_image, mask_image, prompt_edit, model_edit, size_edit, n_edit, config_state],
        outputs=[status_edit, out_edit]
    )

    # URL 参考图功能
    def do_ref(url, p, neg, mdl, sz, n, cfg):
        if not url.strip():
            return "请输入参考图 URL", None
        valid_size = parse_size_input(sz)
        return generate_with_reference(
            prompt=p,
            negative_prompt=neg,
            model=mdl,
            size=valid_size,
            n=n,
            reference_url=url,
            base_url=cfg["base_url"],
            api_key=cfg["api_key"],
            timeout=cfg.get("timeout", 180)
        )

    btn_ref.click(
        do_ref,
        inputs=[ref_url, prompt_ref, neg_ref, model_ref, size_ref, n_ref, config_state],
        outputs=[status_ref, out_ref]
    )

    # ===== 异步功能事件绑定 =====
    
    # 异步文生图 - 提交任务
    def do_async_txt2img_submit(p, neg, mdl, sz, cfg):
        valid_size = parse_size_input(sz)
        status_msg, img, task_id = generate_text_to_image_async(
            prompt=p,
            negative_prompt=neg,
            model=mdl,
            size=valid_size,
            base_url=cfg["base_url"],
            api_key=cfg["api_key"],
            timeout=30
        )
        
        # 添加到历史记录
        if task_id:
            add_task_to_history(
                task_id=task_id,
                task_type="async_txt2img",
                prompt=p,
                model=mdl,
                size=valid_size,
                status="waiting"
            )
        
        return status_msg, task_id

    async_submit_btn.click(
        do_async_txt2img_submit,
        inputs=[async_prompt_txt, async_negative_txt, async_model_txt, async_size_txt, config_state],
        outputs=[async_status_txt, async_task_id_txt]
    )
    
    # 异步文生图 - 查询任务
    def do_async_query(tid, cfg):
        status_msg, img, task_status = query_async_task(
            task_id=tid,
            base_url=cfg["base_url"],
            api_key=cfg["api_key"],
            timeout=30
        )
        return status_msg, img

    query_btn.click(
        do_async_query,
        inputs=[query_task_id, config_state],
        outputs=[async_result_status, async_result_img]
    )
    
    # 异步文生图 - 刷新按钮 (自动从 Task ID 框读取)
    refresh_btn.click(
        do_async_query,
        inputs=[async_task_id_txt, config_state],
        outputs=[async_result_status, async_result_img]
    )
    
    # 异步编辑 - 提交任务
    def do_async_edit_submit(img, mask, p, mdl, sz, cfg):
        if img is None:
            return "请上传源图像", ""
        valid_size = parse_size_input(sz)
        status_msg, result_img, task_id = edit_image_async(
            prompt=p,
            image=img,
            mask=mask,
            model=mdl,
            size=valid_size,
            base_url=cfg["base_url"],
            api_key=cfg["api_key"],
            timeout=30
        )
        
        # 添加到历史记录
        if task_id:
            add_task_to_history(
                task_id=task_id,
                task_type="async_edit",
                prompt=p,
                model=mdl,
                size=valid_size,
                status="waiting"
            )
        
        return status_msg, task_id

    async_edit_submit_btn.click(
        do_async_edit_submit,
        inputs=[async_input_image, async_mask_image, async_prompt_edit, async_model_edit, async_size_edit, config_state],
        outputs=[async_edit_status_txt, async_edit_task_id_txt]
    )
    
    # 异步编辑 - 查询任务
    def do_async_edit_query(tid, cfg):
        status_msg, img, task_status = query_async_task(
            task_id=tid,
            base_url=cfg["base_url"],
            api_key=cfg["api_key"],
            timeout=30
        )
        return status_msg, img

    async_edit_query_btn.click(
        do_async_edit_query,
        inputs=[async_edit_query_task_id, config_state],
        outputs=[async_edit_result_status, async_edit_result_img]
    )
    
    # 异步编辑 - 刷新按钮
    async_edit_refresh_btn.click(
        do_async_edit_query,
        inputs=[async_edit_task_id_txt, config_state],
        outputs=[async_edit_result_status, async_edit_result_img]
    )
    
    # ===== 异步文生视频功能 =====
    def do_async_txt2vid_submit(prompt, model, cfg):
        status_msg, video_path, task_id = generate_text_to_video_async(
            prompt=prompt,
            model=model,
            duration=10,
            base_url=cfg["base_url"],
            api_key=cfg["api_key"],
            timeout=cfg.get("timeout", 60)
        )
        add_task_to_history(
            task_id=task_id,
            task_type="async_txt2vid",
            prompt=prompt,
            model=model,
            size="",
            status="waiting"
        )
        return status_msg, task_id

    async_txt2vid_submit_btn.click(
        do_async_txt2vid_submit,
        inputs=[async_txt2vid_prompt, async_txt2vid_model, config_state],
        outputs=[async_txt2vid_status_txt, async_txt2vid_task_id_txt]
    )
    
    # 异步文生视频 - 查询任务
    def do_async_txt2vid_query(tid, cfg):
        return query_video_async_task(
            task_id=tid,
            base_url=cfg["base_url"],
            api_key=cfg["api_key"],
            timeout=30
        )

    async_txt2vid_query_btn.click(
        do_async_txt2vid_query,
        inputs=[async_txt2vid_query_task_id, config_state],
        outputs=[async_txt2vid_result_status, async_txt2vid_result_video]
    )
    
    # 异步文生视频 - 刷新按钮
    async_txt2vid_refresh_btn.click(
        do_async_txt2vid_query,
        inputs=[async_txt2vid_task_id_txt, config_state],
        outputs=[async_txt2vid_result_status, async_txt2vid_result_video]
    )
    
    # ===== 异步图生视频功能 =====
    def do_async_img2vid_submit(prompt, image, model, cfg):
        image_url = ""
        if image is not None:
            img_buffer = io.BytesIO()
            image.save(img_buffer, format="PNG")
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
            image_url = f"data:image/png;base64,{img_base64}"
        
        status_msg, video_path, task_id = generate_image_to_video_async(
            prompt=prompt,
            image_url=image_url,
            model=model,
            duration=10,
            base_url=cfg["base_url"],
            api_key=cfg["api_key"],
            timeout=cfg.get("timeout", 60)
        )
        add_task_to_history(
            task_id=task_id,
            task_type="async_img2vid",
            prompt=prompt,
            model=model,
            size="",
            status="waiting"
        )
        return status_msg, task_id

    async_img2vid_submit_btn.click(
        do_async_img2vid_submit,
        inputs=[async_img2vid_prompt, async_img2vid_input_image, async_img2vid_model, config_state],
        outputs=[async_img2vid_status_txt, async_img2vid_task_id_txt]
    )
    
    # 异步图生视频 - 查询任务
    def do_async_img2vid_query(tid, cfg):
        return query_video_async_task(
            task_id=tid,
            base_url=cfg["base_url"],
            api_key=cfg["api_key"],
            timeout=30
        )

    async_img2vid_query_btn.click(
        do_async_img2vid_query,
        inputs=[async_img2vid_query_task_id, config_state],
        outputs=[async_img2vid_result_status, async_img2vid_result_video]
    )
    
    # 异步图生视频 - 刷新按钮
    async_img2vid_refresh_btn.click(
        do_async_img2vid_query,
        inputs=[async_img2vid_task_id_txt, config_state],
        outputs=[async_img2vid_result_status, async_img2vid_result_video]
    )
    
    # ===== 任务队列管理功能 =====
    
    # 从 Dataframe 获取所有 Task ID
    def get_all_task_ids(df):
        logger.debug(f"df 类型: {type(df)}")
        
        if df is None:
            return []
        
        # 处理 pandas DataFrame
        import pandas as pd
        if isinstance(df, pd.DataFrame):
            logger.debug(f"pandas DataFrame, 行数: {len(df)}")
            if len(df) == 0:
                return []
            
            task_ids = []
            for idx, row in df.iterrows():
                task_id = str(row['Task ID']).strip()
                if task_id and len(task_id) > 5:
                    task_ids.append(task_id)
            
            logger.debug(f"pandas 最终 Task ID 列表: {task_ids}")
            return task_ids
        
        # 处理普通列表格式（兼容旧版）
        logger.debug(f"df 内容: {df}")
        task_ids = []
        for i, row in enumerate(df):
            if isinstance(row, (list, tuple)) and len(row) >= 1:
                task_id = str(row[0]).strip()
                if task_id and len(task_id) > 5 and task_id not in ["Task ID", "类型", "状态", "提示词", "模型", "时间"]:
                    task_ids.append(task_id)
        
        logger.debug(f"最终 Task ID 列表: {task_ids}")
        return task_ids
    
    # 全选
    def select_all_tasks(df):
        all_ids = get_all_task_ids(df)
        return ", ".join(all_ids)
    
    # 取消全选
    def select_none_tasks(df):
        return ""
    
    # 反选
    def select_inverse_tasks(df, current_selected):
        all_ids = get_all_task_ids(df)
        current_ids = [id.strip() for id in current_selected.split(",") if id.strip()]
        
        # 反选：在所有 ID 中但不在当前选择中的 ID
        inverse_ids = [id for id in all_ids if id not in current_ids]
        return ", ".join(inverse_ids)
    
    # 加载任务列表
    def load_task_list(date_val, type_val):
        # 使用 SQLite 查询
        history = db_get_tasks(date_str=date_val if date_val else None, task_type=type_val if type_val != "all" else None, limit=100)
        
        # 转换为表格数据
        table_data = []
        for task in history:
            if task["task_type"] == "async_txt2img":
                task_type_name = "文生图"
            elif task["task_type"] == "async_edit":
                task_type_name = "图像编辑"
            elif task["task_type"] == "async_txt2vid":
                task_type_name = "文生视频"
            elif task["task_type"] == "async_img2vid":
                task_type_name = "图生视频"
            else:
                task_type_name = "其他"
            time_str = task["created_at"].replace("T", " ")[:19]
            table_data.append([
                task["task_id"],
                task_type_name,
                task["status"],
                task["prompt"][:30] + "..." if len(task["prompt"]) > 30 else task["prompt"],
                task["model"],
                time_str
            ])
        
        # 获取可用日期列表
        dates = db_get_all_dates()
        date_choices = [(d, d) for d in dates]
        date_choices.insert(0, ("全部", ""))
        
        return table_data, gr.update(choices=date_choices, value=date_val if date_val else "")
    
    # 刷新历史列表
    refresh_history_btn.click(
        load_task_list,
        inputs=[filter_date, filter_type],
        outputs=[task_list, filter_date]
    )
    
    # 全选按钮
    select_all_btn.click(
        select_all_tasks,
        inputs=[task_list],
        outputs=[selected_task_ids]
    )
    
    # 取消全选按钮
    select_none_btn.click(
        select_none_tasks,
        inputs=[task_list],
        outputs=[selected_task_ids]
    )
    
    # 反选按钮
    select_inverse_btn.click(
        select_inverse_tasks,
        inputs=[task_list, selected_task_ids],
        outputs=[selected_task_ids]
    )
    
    # 日期筛选变化
    filter_date.change(
        load_task_list,
        inputs=[filter_date, filter_type],
        outputs=[task_list, filter_date]
    )
    
    # 类型筛选变化
    filter_type.change(
        load_task_list,
        inputs=[filter_date, filter_type],
        outputs=[task_list, filter_date]
    )
    
    # 选择任务 - 支持多选
    selected_task_ids_list = []
    current_task_list_cache = []  # 缓存当前任务列表
    
    def select_task(evt: gr.SelectData):
        global current_task_list_cache
        
        # 获取当前筛选条件下的任务列表
        current_date = filter_date.value if filter_date.value else None
        current_type = filter_type.value if filter_type.value != "all" else None
        current_task_list_cache = db_get_tasks(
            date_str=current_date if current_date else None,
            task_type=current_type,
            limit=100
        )
        
        # 使用 evt.index 获取行索引，然后从当前缓存的任务列表中查找
        if hasattr(evt, 'index') and evt.index:
            row_idx = evt.index[0] if isinstance(evt.index, (list, tuple)) else evt.index
            if 0 <= row_idx < len(current_task_list_cache):
                task = current_task_list_cache[row_idx]
                task_id = task["task_id"]
                print(f"[选择任务] 选中行 {row_idx}, Task ID: {task_id}")
                
                # 切换选中状态
                if task_id in selected_task_ids_list:
                    selected_task_ids_list.remove(task_id)
                else:
                    selected_task_ids_list.append(task_id)
                
                # 更新显示的 Task ID 列表
                return ", ".join(selected_task_ids_list)
        
        # 备用方案：直接从 evt.value 获取
        if evt.value:
            task_id = str(evt.value).strip()
            print(f"[选择任务 - 备用] Task ID: {task_id}")
            if task_id in selected_task_ids_list:
                selected_task_ids_list.remove(task_id)
            else:
                selected_task_ids_list.append(task_id)
            return ", ".join(selected_task_ids_list)
        
        return ""
    
    task_list.select(
        select_task,
        outputs=[selected_task_ids]
    )
    
    # 批量查询选中任务
    def batch_query_tasks(task_ids_str, cfg):
        if not task_ids_str:
            return "请先选择任务", None, None
        
        task_ids = [tid.strip() for tid in task_ids_str.split(",") if tid.strip()]
        if not task_ids:
            return "没有有效的 Task ID", None, None
        
        # 逐个查询任务状态
        messages = []
        last_img = None
        last_video = None
        last_status = None
        
        for task_id in task_ids:
            print(f"[批量查询] 查询 {task_id}")
            
            # 先获取任务类型
            task = db_get_task_by_id(task_id)
            task_type = task.get("task_type") if task else None
            
            if task_type in ["async_txt2vid", "async_img2vid"]:
                # 视频任务
                status_msg, video_url, task_status = query_video_async_task(
                    task_id=task_id,
                    base_url=cfg["base_url"],
                    api_key=cfg["api_key"],
                    timeout=30
                )
                if video_url:
                    last_video = video_url
            else:
                # 图像任务
                status_msg, img, task_status = query_async_task(
                    task_id=task_id,
                    base_url=cfg["base_url"],
                    api_key=cfg["api_key"],
                    timeout=30
                )
                if img:
                    last_img = img
            
            # 更新历史记录
            if task_status in ["success", "failure", "cancelled"]:
                update_task_status(task_id, task_status)
            
            messages.append(f"{task_id}: {status_msg.split(chr(10))[0]}")
        
        result_msg = "🔍 批量查询结果\n\n" + "\n".join(messages)
        return result_msg, last_img, last_video
    
    batch_query_btn.click(
        batch_query_tasks,
        inputs=[selected_task_ids, config_state],
        outputs=[task_detail_status, task_detail_img, task_detail_video]
    )
    
    # 批量下载选中任务
    def batch_download_tasks(task_ids_str, cfg):
        if not task_ids_str:
            return "请先选择任务", None
        
        task_ids = [tid.strip() for tid in task_ids_str.split(",") if tid.strip()]
        if not task_ids:
            return "没有有效的 Task ID", None
        
        # 确保 outputs 目录存在
        outputs_dir = Path("outputs")
        outputs_dir.mkdir(exist_ok=True)
        
        downloaded_count = 0
        failed_count = 0
        messages = []
        
        for task_id in task_ids:
            try:
                # 从数据库获取任务信息
                task = db_get_task_by_id(task_id)
                if not task:
                    messages.append(f"❌ {task_id}: 任务不存在")
                    failed_count += 1
                    continue
                
                # 检查是否有 file_url
                file_url = task.get("file_url")
                if not file_url:
                    # 尝试从 result 中获取
                    result = task.get("result")
                    if result:
                        try:
                            result_data = json.loads(result) if isinstance(result, str) else result
                            file_url = result_data.get("file_url")
                        except:
                            pass
                
                # 如果还是没有 file_url 但状态是 success，尝试重新查询
                if not file_url and task.get("status") == "success":
                    print(f"[批量下载] {task_id} 状态为 success 但无 file_url，尝试重新查询...")
                    try:
                        status_msg, img, task_status = query_async_task(
                            task_id=task_id,
                            base_url=cfg["base_url"],
                            api_key=cfg["api_key"],
                            timeout=30
                        )
                        # 重新获取任务信息
                        task = db_get_task_by_id(task_id)
                        file_url = task.get("file_url") if task else None
                        if file_url:
                            print(f"[批量下载] 重新查询获取到 file_url: {file_url}")
                    except Exception as e:
                        print(f"[批量下载] 重新查询失败：{e}")
                
                if not file_url:
                    messages.append(f"⚠️ {task_id}: 无下载地址 (请先查询任务状态)")
                    failed_count += 1
                    continue
                
                # 创建日期目录
                date_str = task["created_at"][:10]
                date_dir = outputs_dir / date_str
                date_dir.mkdir(exist_ok=True)
                
                # 下载文件
                print(f"[批量下载] 下载 {task_id} -> {file_url}")
                img_resp = requests.get(file_url, timeout=30)
                img_resp.raise_for_status()
                
                # 生成文件名
                task_type = task["task_type"]
                # 检测文件类型
                content_type = img_resp.headers.get("Content-Type", "")
                file_url_lower = file_url.lower()
                
                if task_type in ["async_txt2vid", "async_img2vid"] or "video" in content_type or any(file_url_lower.endswith(ext) for ext in ('.mp4', '.webm', '.mov', '.avi')):
                    file_ext = ".mp4"
                    task_type_display = "txt2vid" if task_type == "async_txt2vid" else "img2vid"
                else:
                    file_ext = ".png"
                    task_type_display = "txt2img" if task_type == "async_txt2img" else "edit"
                
                file_name = f"{task_type_display}_{task_id[:16]}{file_ext}"
                file_path = date_dir / file_name
                
                # 保存文件
                with open(file_path, "wb") as f:
                    f.write(img_resp.content)
                
                # 更新数据库中的下载路径
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE tasks SET download_path = ?
                    WHERE task_id = ?
                ''', (str(file_path), task_id))
                conn.commit()
                conn.close()
                
                downloaded_count += 1
                messages.append(f"✅ {task_id}: 已保存到 {file_path}")
                
            except Exception as e:
                failed_count += 1
                messages.append(f"❌ {task_id}: 下载失败 - {str(e)}")
                print(f"[批量下载] {task_id} 失败：{e}")
        
        result_msg = f"📥 批量下载完成\n✅ 成功：{downloaded_count}\n❌ 失败：{failed_count}\n\n" + "\n".join(messages)
        return result_msg, None, None
    
    batch_download_btn.click(
        batch_download_tasks,
        inputs=[selected_task_ids, config_state],
        outputs=[task_detail_status, task_detail_img, task_detail_video]
    )
    
    # 清空历史记录
    def clear_history():
        db_clear_history()
        selected_task_ids_list.clear()
        return [], gr.update(choices=[], value=""), "✅ 历史记录已清空", ""
    
    clear_history_btn.click(
        clear_history,
        outputs=[task_list, filter_date, task_detail_status, selected_task_ids]
    )
    
    # 页面加载时初始化任务列表
    def on_page_load():
        history = load_task_history()
        dates = db_get_all_dates()
        date_choices = [(d, d) for d in dates]
        date_choices.insert(0, ("全部", ""))
        
        # 加载最近的任务
        table_data = []
        for task in history[:50]:  # 只显示最近 50 条
            task_type_name = "文生图" if task["task_type"] == "async_txt2img" else "图像编辑"
            time_str = task["created_at"].replace("T", " ")[:19]
            table_data.append([
                task["task_id"],
                task_type_name,
                task["status"],
                task["prompt"][:30] + "..." if len(task["prompt"]) > 30 else task["prompt"],
                task["model"],
                time_str
            ])
        
        return table_data, gr.update(choices=date_choices, value=""), "", ""
    
    demo.load(on_page_load, outputs=[task_list, filter_date, task_detail_status, selected_task_ids])

    # 启动时判断是否直接显示主界面
    def on_load(cfg):
        if cfg.get("api_key", "").strip():
            return gr.update(visible=False), gr.update(visible=True)
        return gr.update(visible=True), gr.update(visible=False)

    demo.load(on_load, inputs=config_state, outputs=[config_col, main_col])
    
    # 底部作者信息
    gr.Markdown("""
    <div class="author-footer">
        <p style="margin: 10px 0; font-size: 16px;">
            <strong>🎨 白嫖大师</strong> - 让AI不再昂贵，让创意不受限制
        </p>
        <p style="margin: 10px 0; font-size: 14px; color: #666;">
            作者：<strong>你们喜爱的老王</strong> | 
            <a href="https://space.bilibili.com/97727630" target="_blank">🎬 B站主页</a> | 
            <a href="https://github.com/ops120/bai-piao-master" target="_blank">⭐ GitHub项目</a>
        </p>
        <p style="margin: 5px 0; font-size: 12px; color: #999;">
            如果觉得好用，欢迎点赞、关注、分享！
        </p>
    </div>
    """)

if __name__ == "__main__":
    demo.launch(
        server_port=11111,
        share=False,
        inbrowser=True
    )