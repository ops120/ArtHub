import gradio as gr
import sys
import os
import json
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core import VendorManager, APIGateway, ConfigManager, TaskType
from src.models.vendor import VendorConfig

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

VENDOR_TEMPLATES = {
    "moark": {
        "name": "模力方舟",
        "base_url": "https://api.moark.com/v1",
        "description": "支持文生图、图像编辑、文生视频、图生视频",
        "support_text2img": True,
        "support_edit": True,
        "support_txt2vid": True,
        "support_img2vid": True,
        "text2img_models": ["FLUX.1-dev", "LongCat-Image", "flux-1-schnell", "Qwen-Image-2512"],
        "edit_models": ["LongCat-Image-Edit", "Qwen-Image-Edit-2511"],
        "txt2vid_models": ["stepvideo-t2v"],
        "img2vid_models": ["LTX-2"]
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "description": "DALL-E 图像生成",
        "support_text2img": True,
        "support_edit": False,
        "support_txt2vid": False,
        "support_img2vid": False,
        "text2img_models": ["dall-e-3", "dall-e-2"],
        "edit_models": [],
        "txt2vid_models": [],
        "img2vid_models": []
    },
    "siliconflow": {
        "name": "硅基流动",
        "base_url": "https://api.siliconflow.cn/v1",
        "description": "多种开源模型",
        "support_text2img": True,
        "support_edit": False,
        "support_txt2vid": False,
        "support_img2vid": False,
        "text2img_models": ["FLUX.1-dev", "stable-diffusion-xl-base-1.0"],
        "edit_models": [],
        "txt2vid_models": [],
        "img2vid_models": []
    },
    "dashscope": {
        "name": "阿里云 DashScope",
        "base_url": "https://dashscope.aliyuncs.com/api/v1",
        "description": "阿里云通义万相",
        "support_text2img": True,
        "support_edit": False,
        "support_txt2vid": False,
        "support_img2vid": False,
        "text2img_models": ["wanx-style-transfer"],
        "edit_models": [],
        "txt2vid_models": [],
        "img2vid_models": []
    }
}

class AIClientApp:
    def __init__(self):
        self.config_manager = ConfigManager("conf/config.json")
        self.vendor_manager = VendorManager()
        self.api_gateway = APIGateway(self.vendor_manager)
        self._load_vendors()
    
    def _load_vendors(self):
        vendors_config = self.config_manager.get_vendors_config()
        for vendor_dict in vendors_config:
            vendor = VendorConfig.from_dict(vendor_dict)
            self.vendor_manager.add_vendor(vendor)
        logger.info(f"加载了 {len(vendors_config)} 个厂商")
    
    def get_enabled_vendors(self):
        vendors = self.vendor_manager.list_vendors(enabled_only=True)
        return [f"{v.name} ({v.vendor_id})" for v in vendors]
    
    def get_models_for_task(self, vendor_choice, task_type):
        if not vendor_choice:
            return []
        vendor_id = vendor_choice.split("(")[-1].rstrip(")")
        vendor = self.vendor_manager.get_vendor(vendor_id)
        if not vendor:
            return []
        
        models = []
        if task_type == "text2img" and vendor.support_text2img:
            models = vendor.text2img_models
        elif task_type == "edit" and vendor.support_edit:
            models = vendor.edit_models
        elif task_type == "txt2vid" and vendor.support_txt2vid:
            models = vendor.txt2vid_models
        elif task_type == "img2vid" and vendor.support_img2vid:
            models = vendor.img2vid_models
        return models if models else []
    
    def apply_template(self, template_key):
        if template_key not in VENDOR_TEMPLATES:
            return "未找到模板", "", "", "", "", "", "", "", "", "", "", ""
        
        template = VENDOR_TEMPLATES[template_key]
        return (
            template["name"],
            template["base_url"],
            template["description"],
            ",".join(template["text2img_models"]),
            ",".join(template["edit_models"]),
            ",".join(template["txt2vid_models"]),
            ",".join(template["img2vid_models"]),
            "✅ 已应用模板"
        )
    
    def add_vendor(self, name, vendor_id, base_url, api_key, description,
                   txt2img_models, edit_models, txt2vid_models, img2vid_models):
        try:
            vendor = VendorConfig(
                vendor_id=vendor_id,
                name=name,
                base_url=base_url,
                api_key=api_key,
                description=description,
                enabled=True,
                support_text2img=bool(txt2img_models),
                support_edit=bool(edit_models),
                support_txt2vid=bool(txt2vid_models),
                support_img2vid=bool(img2vid_models),
                text2img_models=[m.strip() for m in txt2img_models.split(",") if m.strip()],
                edit_models=[m.strip() for m in edit_models.split(",") if m.strip()],
                txt2vid_models=[m.strip() for m in txt2vid_models.split(",") if m.strip()],
                img2vid_models=[m.strip() for m in img2vid_models.split(",") if m.strip()]
            )
            self.vendor_manager.add_vendor(vendor)
            
            vendors = self.config_manager.get_vendors_config()
            vendor_dict = vendor.to_dict()
            
            for i, v in enumerate(vendors):
                if v.get("vendor_id") == vendor_id:
                    vendors[i] = vendor_dict
                    break
            else:
                vendors.append(vendor_dict)
            
            self.config_manager.save_vendors_config(vendors)
            return f"✅ 添加厂商成功: {name}"
        except Exception as e:
            return f"❌ 添加失败: {str(e)}"
    
    def generate_image(self, vendor_choice, model, prompt, negative_prompt, size, n):
        if not vendor_choice or not prompt:
            return None, "请选择厂商并输入提示词"
        
        vendor_id = vendor_choice.split("(")[-1].rstrip(")")
        
        try:
            response = self.api_gateway.generate(
                vendor_id=vendor_id,
                task_type=TaskType.TEXT2IMG,
                prompt=prompt,
                model=model,
                negative_prompt=negative_prompt,
                size=size,
                n=n
            )
            
            if response.success and response.data:
                import base64
                from PIL import Image
                import io
                
                img_data = response.data[0]
                if img_data.b64:
                    img_bytes = base64.b64decode(img_data.b64)
                    img = Image.open(io.BytesIO(img_bytes))
                    return img, f"生成成功！耗时: {response.processing_time:.2f}秒"
            
            return None, f"生成失败: {response.error}"
        except Exception as e:
            logger.error(f"生成失败: {e}")
            return None, f"错误: {str(e)}"
    
    def edit_image(self, vendor_choice, model, prompt, image, mask, size):
        if not vendor_choice or not prompt or image is None:
            return None, "请选择厂商、输入提示词并上传图片"
        
        vendor_id = vendor_choice.split("(")[-1].rstrip(")")
        
        try:
            import base64
            from PIL import Image
            import io
            
            img_pil = Image.fromarray(image)
            buffered = io.BytesIO()
            img_pil.save(buffered, format="PNG")
            img_b64 = base64.b64encode(buffered.getvalue()).decode()
            
            mask_b64 = None
            if mask is not None:
                mask_pil = Image.fromarray(mask)
                buffered = io.BytesIO()
                mask_pil.save(buffered, format="PNG")
                mask_b64 = base64.b64encode(buffered.getvalue()).decode()
            
            response = self.api_gateway.generate(
                vendor_id=vendor_id,
                task_type=TaskType.IMAGE_EDIT,
                prompt=prompt,
                model=model,
                image=img_b64,
                mask=mask_b64,
                size=size
            )
            
            if response.success and response.data:
                img_data = response.data[0]
                if img_data.b64:
                    img_bytes = base64.b64decode(img_data.b64)
                    result_img = Image.open(io.BytesIO(img_bytes))
                    return result_img, f"编辑成功！"
            
            return None, f"编辑失败: {response.error}"
        except Exception as e:
            logger.error(f"编辑失败: {e}")
            return None, f"错误: {str(e)}"
    
    def generate_video_async(self, vendor_choice, model, prompt, duration):
        if not vendor_choice or not prompt:
            return "请选择厂商并输入提示词"
        
        vendor_id = vendor_choice.split("(")[-1].rstrip(")")
        
        try:
            response = self.api_gateway.generate_async(
                vendor_id=vendor_id,
                task_type=TaskType.TEXT2VIDEO,
                prompt=prompt,
                model=model,
                duration=duration
            )
            
            if response.success:
                return f"任务提交成功！Task ID: {response.task_id}\n状态: {response.status}"
            else:
                return f"提交失败: {response.error}"
        except Exception as e:
            logger.error(f"提交失败: {e}")
            return f"错误: {str(e)}"
    
    def generate_image_async(self, vendor_choice, model, prompt, negative_prompt, size):
        if not vendor_choice or not prompt:
            return "请选择厂商并输入提示词", ""
        
        vendor_id = vendor_choice.split("(")[-1].rstrip(")")
        
        try:
            response = self.api_gateway.generate_async(
                vendor_id=vendor_id,
                task_type=TaskType.TEXT2IMG,
                prompt=prompt,
                model=model,
                negative_prompt=negative_prompt,
                size=size
            )
            
            if response.success:
                self._add_task(response.task_id, "async_txt2img", prompt, model, size)
                return f"任务提交成功！Task ID: {response.task_id}", response.task_id
            else:
                return f"提交失败: {response.error}", ""
        except Exception as e:
            logger.error(f"提交失败: {e}")
            return f"错误: {str(e)}", ""
    
    def edit_image_async(self, vendor_choice, model, prompt, image, mask, size):
        if not vendor_choice or not prompt or image is None:
            return "请选择厂商、输入提示词并上传图片", ""
        
        vendor_id = vendor_choice.split("(")[-1].rstrip(")")
        
        try:
            import base64
            from PIL import Image
            import io
            
            img_pil = Image.fromarray(image)
            buffered = io.BytesIO()
            img_pil.save(buffered, format="PNG")
            img_b64 = base64.b64encode(buffered.getvalue()).decode()
            
            mask_b64 = None
            if mask is not None:
                mask_pil = Image.fromarray(mask)
                buffered = io.BytesIO()
                mask_pil.save(buffered, format="PNG")
                mask_b64 = base64.b64encode(buffered.getvalue()).decode()
            
            response = self.api_gateway.generate_async(
                vendor_id=vendor_id,
                task_type=TaskType.IMAGE_EDIT,
                prompt=prompt,
                model=model,
                image=img_b64,
                mask=mask_b64,
                size=size
            )
            
            if response.success:
                self._add_task(response.task_id, "async_edit", prompt, model, size)
                return f"任务提交成功！Task ID: {response.task_id}", response.task_id
            else:
                return f"提交失败: {response.error}", ""
        except Exception as e:
            logger.error(f"提交失败: {e}")
            return f"错误: {str(e)}", ""
    
    def query_task(self, vendor_choice, task_id):
        if not vendor_choice or not task_id:
            return "请选择厂商并输入Task ID", None
        
        vendor_id = vendor_choice.split("(")[-1].rstrip(")")
        
        try:
            response = self.api_gateway.query_task(
                vendor_id=vendor_id,
                task_id=task_id
            )
            
            if response.success:
                status = f"状态: {response.status}"
                img = None
                if response.result and response.result.get("image"):
                    import base64
                    from PIL import Image
                    import io
                    img_bytes = base64.b64decode(response.result["image"])
                    img = Image.open(io.BytesIO(img_bytes))
                return status, img
            else:
                return f"查询失败: {response.error}", None
        except Exception as e:
            logger.error(f"查询失败: {e}")
            return f"错误: {str(e)}", None
    
    def _add_task(self, task_id, task_type, prompt, model, size):
        try:
            import sqlite3
            from datetime import datetime
            conn = sqlite3.connect("data/tasks.db")
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute('''
                INSERT OR REPLACE INTO tasks (task_id, task_type, prompt, model, size, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (task_id, task_type, prompt, model, size, "waiting", now, now))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"添加任务失败: {e}")
    
    def get_task_history(self, filter_type="all"):
        try:
            import sqlite3
            conn = sqlite3.connect("data/tasks.db")
            cursor = conn.cursor()
            
            if filter_type == "all":
                cursor.execute('SELECT task_id, task_type, status, prompt, model, size, created_at FROM tasks ORDER BY created_at DESC LIMIT 100')
            else:
                cursor.execute('SELECT task_id, task_type, status, prompt, model, size, created_at FROM tasks WHERE task_type = ? ORDER BY created_at DESC LIMIT 100', (filter_type,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [[r[0], r[1], r[2], r[3][:50] if r[3] else "", r[4], r[5], r[6][:19]] for r in rows]
        except Exception as e:
            logger.error(f"获取任务历史失败: {e}")
            return []
    
    def refresh_task(self, vendor_choice, task_id):
        return self.query_task(vendor_choice, task_id)
    
    def get_all_tasks(self, filter_type="all"):
        try:
            import sqlite3
            conn = sqlite3.connect("data/tasks.db")
            cursor = conn.cursor()
            
            if filter_type == "all":
                cursor.execute('SELECT task_id, task_type, status, prompt, model, size, created_at FROM tasks ORDER BY created_at DESC')
            else:
                cursor.execute('SELECT task_id, task_type, status, prompt, model, size, created_at FROM tasks WHERE task_type = ? ORDER BY created_at DESC', (filter_type,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [[r[0], r[1], r[2], r[3][:50] if r[3] else "", r[4], r[5], r[6][:19]] for r in rows]
        except Exception as e:
            logger.error(f"获取任务失败: {e}")
            return []
    
    def download_all_tasks(self, vendor_choice, task_ids_str):
        if not vendor_choice or not task_ids_str:
            return "请选择厂商并输入Task ID"
        
        vendor_id = vendor_choice.split("(")[-1].rstrip(")")
        task_ids = [tid.strip() for tid in task_ids_str.split(",") if tid.strip()]
        
        if not task_ids:
            return "请选择要下载的任务"
        
        import os
        from pathlib import Path
        download_dir = Path("downloads")
        download_dir.mkdir(exist_ok=True)
        
        results = []
        for task_id in task_ids:
            try:
                response = self.api_gateway.query_task(vendor_id=vendor_id, task_id=task_id)
                logger.debug(f"查询结果: success={response.success}, status={response.status}, result={response.result}")
                
                if response.success:
                    img_data = None
                    file_url = None
                    
                    if response.result:
                        img_data = response.result.get("image") or response.result.get("b64_json")
                        file_url = response.result.get("file_url") or response.result.get("url")
                    
                    if file_url:
                        import requests as req
                        resp = req.get(file_url, timeout=30)
                        if resp.status_code == 200:
                            from PIL import Image
                            import io
                            img = Image.open(io.BytesIO(resp.content))
                            
                            ext = "png"
                            if file_url.endswith(".mp4") or file_url.endswith(".webm"):
                                ext = "mp4"
                            
                            filepath = download_dir / f"{task_id}.{ext}"
                            img.save(filepath)
                            results.append(f"✅ {task_id} -> {filepath}")
                        else:
                            results.append(f"❌ {task_id}: 下载失败 (HTTP {resp.status_code})")
                    elif img_data:
                        import base64
                        from PIL import Image
                        import io
                        
                        img_bytes = base64.b64decode(img_data)
                        img = Image.open(io.BytesIO(img_bytes))
                        
                        ext = "png"
                        if task_id.startswith("VID"):
                            ext = "mp4"
                        
                        filepath = download_dir / f"{task_id}.{ext}"
                        img.save(filepath)
                        results.append(f"✅ {task_id} -> {filepath}")
                    else:
                        results.append(f"❌ {task_id}: 无图片数据 (状态: {response.status})")
                else:
                    results.append(f"❌ {task_id}: {response.error}")
            except Exception as e:
                results.append(f"❌ {task_id}: {str(e)}")
        
        return "\n".join(results)
    
    def image_to_video_async(self, vendor_choice, model, prompt, image, duration):
        if not vendor_choice or not prompt or image is None:
            return "请选择厂商、输入提示词并上传图片"
        
        vendor_id = vendor_choice.split("(")[-1].rstrip(")")
        
        try:
            import base64
            from PIL import Image
            import io
            
            img_pil = Image.fromarray(image)
            buffered = io.BytesIO()
            img_pil.save(buffered, format="PNG")
            img_b64 = base64.b64encode(buffered.getvalue()).decode()
            
            response = self.api_gateway.generate_async(
                vendor_id=vendor_id,
                task_type=TaskType.IMAGE2VIDEO,
                prompt=prompt,
                model=model,
                image=img_b64,
                duration=duration
            )
            
            if response.success:
                return f"任务提交成功！Task ID: {response.task_id}\n状态: {response.status}"
            else:
                return f"提交失败: {response.error}"
        except Exception as e:
            logger.error(f"提交失败: {e}")
            return f"错误: {str(e)}"


app = AIClientApp()

try:
    import sqlite3
    from pathlib import Path
    Path("data").mkdir(exist_ok=True)
    conn = sqlite3.connect("data/tasks.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            task_type TEXT NOT NULL,
            prompt TEXT,
            model TEXT,
            size TEXT,
            status TEXT DEFAULT 'waiting',
            result TEXT,
            file_url TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    conn.commit()
    conn.close()
except Exception as e:
    logger.warning(f"初始化任务数据库失败: {e}")

css = """
.gradio-container {max-width: 1400px !important}
"""

with gr.Blocks(title="白嫖大师 - 通用AI客户端", css=css) as demo:
    gr.Markdown("""
    <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; margin-bottom: 20px;">
        <h1 style="color: white; margin: 10px 0; font-size: 32px;">🎨 白嫖大师 - 通用AI客户端</h1>
        <p style="color: white; font-size: 16px;">支持多厂商接入的 AI 图像/视频生成工具</p>
    </div>
    """)
    
    with gr.Tabs():
        with gr.Tab("🏠 厂商管理"):
            gr.Markdown("### 添加新厂商")
            with gr.Row():
                with gr.Column():
                    gr.Markdown("#### 快速开始 - 选择预设模板")
                    template_dropdown = gr.Dropdown(
                        choices=list(VENDOR_TEMPLATES.keys()),
                        label="选择预设模板",
                        value=None
                    )
                    apply_template_btn = gr.Button("应用模板")
                
                with gr.Column():
                    gr.Markdown("#### 或手动填写")
                    with gr.Row():
                        vendor_name = gr.Textbox(label="厂商名称", placeholder="如: 模力方舟")
                        vendor_id = gr.Textbox(label="厂商ID", placeholder="如: moark")
                    
                    base_url = gr.Textbox(label="API 地址", placeholder="https://api.xxx.com/v1")
                    api_key = gr.Textbox(label="API Key", type="password")
                    description = gr.Textbox(label="描述", placeholder="厂商功能描述")
            
            gr.Markdown("#### 支持的功能")
            with gr.Row():
                chk_txt2img = gr.Checkbox(label="文生图", value=True)
                chk_edit = gr.Checkbox(label="图像编辑", value=False)
                chk_txt2vid = gr.Checkbox(label="文生视频", value=False)
                chk_img2vid = gr.Checkbox(label="图生视频", value=False)
            
            with gr.Row():
                txt2img_models = gr.Textbox(label="文生图模型(逗号分隔)", value="FLUX.1-dev")
                edit_models = gr.Textbox(label="编辑模型(逗号分隔)")
            
            with gr.Row():
                txt2vid_models = gr.Textbox(label="文生视频模型(逗号分隔)")
                img2vid_models = gr.Textbox(label="图生视频模型(逗号分隔)")
            
            add_vendor_btn = gr.Button("➕ 添加厂商", variant="primary")
            add_vendor_status = gr.Textbox(label="状态", lines=2)
            
            gr.Markdown("---")
            gr.Markdown("### 已添加的厂商")
            vendors_list = gr.Dataframe(
                headers=["厂商名称", "ID", "API地址", "状态", "功能"],
                datatype=["str", "str", "str", "str", "str"],
                value=[[v.name, v.vendor_id, v.base_url, "✅ 已启用", 
                       f"图:{len(v.text2img_models)} 编:{len(v.edit_models)} 视频:{len(v.txt2vid_models)}"] 
                       for v in app.vendor_manager.list_vendors()]
            )
            
            def on_apply_template(key):
                return app.apply_template(key)
            
            def on_add_vendor(name, vid, url, key, desc, txt, ed, tv, iv):
                return app.add_vendor(name, vid, url, key, desc, txt, ed, tv, iv)
            
            apply_template_btn.click(on_apply_template, template_dropdown, 
                                   [vendor_name, vendor_id, base_url, description, 
                                    txt2img_models, edit_models, txt2vid_models, img2vid_models, add_vendor_status])
            
            add_vendor_btn.click(on_add_vendor, 
                               [vendor_name, vendor_id, base_url, api_key, description,
                                txt2img_models, edit_models, txt2vid_models, img2vid_models],
                               [add_vendor_status])
        
        with gr.Tab("📝 文生图"):
            gr.Markdown("### 文本生成图像")
            
            def get_initial_models():
                vendors = app.get_enabled_vendors()
                if vendors:
                    return app.get_models_for_task(vendors[0], "text2img")
                return []
            
            with gr.Row():
                with gr.Column(scale=1):
                    txt_vendor = gr.Dropdown(choices=app.get_enabled_vendors(), label="选择厂商", value=app.get_enabled_vendors()[0] if app.get_enabled_vendors() else None)
                    txt_model = gr.Dropdown(choices=get_initial_models(), label="选择模型", value=get_initial_models()[0] if get_initial_models() else None)
                    txt_size = gr.Dropdown(choices=["512x512", "768x768", "1024x1024", "1280x720", "1536x1024"], value="1024x1024", label="图像尺寸")
                with gr.Column(scale=2):
                    txt_prompt = gr.Textbox(label="提示词", lines=3, placeholder="描述你想要的图像...")
                    txt_negative = gr.Textbox(label="负提示词", lines=2, placeholder="不想出现的内容...")
            
            with gr.Row():
                txt_n = gr.Slider(1, 4, value=1, step=1, label="生成数量")
            
            txt_btn = gr.Button("🚀 生成图像", variant="primary", size="lg")
            
            with gr.Row():
                txt_output = gr.Image(label="生成结果")
                txt_status = gr.Textbox(label="状态", lines=3)
            
            def update_txt_models(vendor_choice):
                return gr.Dropdown(choices=app.get_models_for_task(vendor_choice, "text2img"))
            
            txt_vendor.change(update_txt_models, txt_vendor, txt_model)
            txt_btn.click(app.generate_image, [txt_vendor, txt_model, txt_prompt, txt_negative, txt_size, txt_n], [txt_output, txt_status])
        
        with gr.Tab("✏️ 图像编辑"):
            gr.Markdown("### 图像编辑")
            
            def get_initial_edit_models():
                vendors = app.get_enabled_vendors()
                if vendors:
                    return app.get_models_for_task(vendors[0], "edit")
                return []
            
            with gr.Row():
                with gr.Column():
                    edit_vendor = gr.Dropdown(choices=app.get_enabled_vendors(), label="选择厂商", value=app.get_enabled_vendors()[0] if app.get_enabled_vendors() else None)
                    edit_model = gr.Dropdown(choices=get_initial_edit_models(), label="选择模型", value=get_initial_edit_models()[0] if get_initial_edit_models() else None)
                    edit_size = gr.Dropdown(choices=["512x512", "768x768", "1024x1024"], value="1024x1024", label="输出尺寸")
                with gr.Column():
                    edit_input = gr.Image(label="上传图片", type="numpy")
                    edit_mask = gr.Image(label="上传蒙版(可选)", type="numpy")
            
            edit_prompt = gr.Textbox(label="编辑指令", lines=2, placeholder="描述你想对图片做什么修改...")
            
            edit_btn = gr.Button("🚀 开始编辑", variant="primary", size="lg")
            
            with gr.Row():
                edit_output = gr.Image(label="编辑结果")
                edit_status = gr.Textbox(label="状态", lines=2)
            
            def update_edit_models(vendor_choice):
                return gr.Dropdown(choices=app.get_models_for_task(vendor_choice, "edit"))
            
            edit_vendor.change(update_edit_models, edit_vendor, edit_model)
            edit_btn.click(app.edit_image, [edit_vendor, edit_model, edit_prompt, edit_input, edit_mask, edit_size], [edit_output, edit_status])
        
        with gr.Tab("🎬 异步文生视频"):
            gr.Markdown("### 异步文本生成视频")
            
            def get_initial_vid_models():
                vendors = app.get_enabled_vendors()
                if vendors:
                    return app.get_models_for_task(vendors[0], "txt2vid")
                return []
            
            with gr.Row():
                with gr.Column():
                    vid_vendor = gr.Dropdown(choices=app.get_enabled_vendors(), label="选择厂商", value=app.get_enabled_vendors()[0] if app.get_enabled_vendors() else None)
                    vid_model = gr.Dropdown(choices=get_initial_vid_models(), label="选择模型", value=get_initial_vid_models()[0] if get_initial_vid_models() else None)
                    vid_duration = gr.Slider(1, 10, value=5, step=1, label="视频时长(秒)")
                with gr.Column():
                    vid_prompt = gr.Textbox(label="提示词", lines=4, placeholder="描述你想要生成的视频...")
            
            vid_btn = gr.Button("📤 提交异步任务", variant="primary", size="lg")
            vid_status = gr.Textbox(label="任务状态", lines=4)
            
            def update_vid_models(vendor_choice):
                return gr.Dropdown(choices=app.get_models_for_task(vendor_choice, "txt2vid"))
            
            vid_vendor.change(update_vid_models, vid_vendor, vid_model)
            vid_btn.click(app.generate_video_async, [vid_vendor, vid_model, vid_prompt, vid_duration], [vid_status])
        
        with gr.Tab("🎥 异步图生视频"):
            gr.Markdown("### 异步图像生成视频")
            
            def get_initial_img2vid_models():
                vendors = app.get_enabled_vendors()
                if vendors:
                    return app.get_models_for_task(vendors[0], "img2vid")
                return []
            
            with gr.Row():
                with gr.Column():
                    img2vid_vendor = gr.Dropdown(choices=app.get_enabled_vendors(), label="选择厂商", value=app.get_enabled_vendors()[0] if app.get_enabled_vendors() else None)
                    img2vid_model = gr.Dropdown(choices=get_initial_img2vid_models(), label="选择模型", value=get_initial_img2vid_models()[0] if get_initial_img2vid_models() else None)
                    img2vid_duration = gr.Slider(1, 10, value=5, step=1, label="视频时长(秒)")
                with gr.Column():
                    img2vid_input = gr.Image(label="上传图片", type="numpy")
            
            img2vid_prompt = gr.Textbox(label="提示词(可选)", lines=2, placeholder="描述图片如何运动...")
            
            img2vid_btn = gr.Button("📤 提交异步任务", variant="primary", size="lg")
            img2vid_status = gr.Textbox(label="任务状态", lines=4)
            
            def update_img2vid_models(vendor_choice):
                return gr.Dropdown(choices=app.get_models_for_task(vendor_choice, "img2vid"))
            
            img2vid_vendor.change(update_img2vid_models, img2vid_vendor, img2vid_model)
            img2vid_btn.click(app.image_to_video_async, [img2vid_vendor, img2vid_model, img2vid_prompt, img2vid_input, img2vid_duration], [img2vid_status])
        
        with gr.Tab("⏳ 异步文生图"):
            gr.Markdown("### 异步文本生成图像")
            
            def get_initial_async_txt2img_models():
                vendors = app.get_enabled_vendors()
                if vendors:
                    return app.get_models_for_task(vendors[0], "text2img")
                return []
            
            with gr.Row():
                with gr.Column():
                    async_txt_vendor = gr.Dropdown(choices=app.get_enabled_vendors(), label="选择厂商", value=app.get_enabled_vendors()[0] if app.get_enabled_vendors() else None)
                    async_txt_model = gr.Dropdown(choices=get_initial_async_txt2img_models(), label="选择模型", value=get_initial_async_txt2img_models()[0] if get_initial_async_txt2img_models() else None)
                    async_txt_size = gr.Dropdown(choices=["512x512", "768x768", "1024x1024"], value="1024x1024", label="图像尺寸")
                with gr.Column():
                    async_txt_prompt = gr.Textbox(label="提示词", lines=4, placeholder="描述你想要的图像...")
                    async_txt_negative = gr.Textbox(label="负提示词", lines=2, placeholder="不想出现的内容...")
            
            async_txt_btn = gr.Button("📤 提交异步任务", variant="primary", size="lg")
            
            with gr.Row():
                async_txt_status = gr.Textbox(label="提交状态", lines=3)
                async_txt_task_id = gr.Textbox(label="Task ID", lines=1)
            
            with gr.Row():
                gr.Markdown("### 查询任务结果")
            with gr.Row():
                query_vendor = gr.Dropdown(choices=app.get_enabled_vendors(), label="选择厂商", value=app.get_enabled_vendors()[0] if app.get_enabled_vendors() else None)
                query_task_id = gr.Textbox(label="Task ID", placeholder="输入Task ID查询...")
                query_btn = gr.Button("🔍 查询")
            
            with gr.Row():
                query_result_img = gr.Image(label="结果图片")
                query_result_status = gr.Textbox(label="状态", lines=3)
            
            def update_async_txt_models(vendor_choice):
                return gr.Dropdown(choices=app.get_models_for_task(vendor_choice, "text2img"))
            
            async_txt_vendor.change(update_async_txt_models, async_txt_vendor, async_txt_model)
            async_txt_btn.click(app.generate_image_async, [async_txt_vendor, async_txt_model, async_txt_prompt, async_txt_negative, async_txt_size], [async_txt_status, async_txt_task_id])
            query_btn.click(app.query_task, [query_vendor, query_task_id], [query_result_status, query_result_img])
        
        with gr.Tab("✏️ 异步图像编辑"):
            gr.Markdown("### 异步图像编辑")
            
            def get_initial_async_edit_models():
                vendors = app.get_enabled_vendors()
                if vendors:
                    return app.get_models_for_task(vendors[0], "edit")
                return []
            
            with gr.Row():
                with gr.Column():
                    async_edit_vendor = gr.Dropdown(choices=app.get_enabled_vendors(), label="选择厂商", value=app.get_enabled_vendors()[0] if app.get_enabled_vendors() else None)
                    async_edit_model = gr.Dropdown(choices=get_initial_async_edit_models(), label="选择模型", value=get_initial_async_edit_models()[0] if get_initial_async_edit_models() else None)
                    async_edit_size = gr.Dropdown(choices=["512x512", "768x768", "1024x1024"], value="1024x1024", label="输出尺寸")
                with gr.Column():
                    async_edit_input = gr.Image(label="上传图片", type="numpy")
                    async_edit_mask = gr.Image(label="上传蒙版(可选)", type="numpy")
            
            async_edit_prompt = gr.Textbox(label="编辑指令", lines=2, placeholder="描述你想对图片做什么修改...")
            
            async_edit_btn = gr.Button("📤 提交异步任务", variant="primary", size="lg")
            
            with gr.Row():
                async_edit_status = gr.Textbox(label="提交状态", lines=3)
                async_edit_task_id = gr.Textbox(label="Task ID", lines=1)
            
            with gr.Row():
                gr.Markdown("### 查询任务结果")
            with gr.Row():
                query_edit_vendor = gr.Dropdown(choices=app.get_enabled_vendors(), label="选择厂商", value=app.get_enabled_vendors()[0] if app.get_enabled_vendors() else None)
                query_edit_task_id = gr.Textbox(label="Task ID", placeholder="输入Task ID查询...")
                query_edit_btn = gr.Button("🔍 查询")
            
            with gr.Row():
                query_edit_result_img = gr.Image(label="结果图片")
                query_edit_result_status = gr.Textbox(label="状态", lines=3)
            
            def update_async_edit_models(vendor_choice):
                return gr.Dropdown(choices=app.get_models_for_task(vendor_choice, "edit"))
            
            async_edit_vendor.change(update_async_edit_models, async_edit_vendor, async_edit_model)
            async_edit_btn.click(app.edit_image_async, [async_edit_vendor, async_edit_model, async_edit_prompt, async_edit_input, async_edit_mask, async_edit_size], [async_edit_status, async_edit_task_id])
            query_edit_btn.click(app.query_task, [query_edit_vendor, query_edit_task_id], [query_edit_result_status, query_edit_result_img])
        
        with gr.Tab("📋 任务队列"):
            gr.Markdown("### 任务队列管理")
            
            with gr.Row():
                filter_type = gr.Dropdown(
                    choices=[
                        ("全部", "all"),
                        ("文生图", "async_txt2img"),
                        ("图像编辑", "async_edit"),
                        ("文生视频", "async_txt2vid"),
                        ("图生视频", "async_img2vid")
                    ],
                    value="all",
                    label="任务类型筛选"
                )
                refresh_history_btn = gr.Button("🔄 刷新列表", variant="secondary")
            
            with gr.Row():
                gr.Markdown("### 任务列表 - 点击Task ID可复制")
            
            task_list = gr.Dataframe(
                headers=["Task ID", "类型", "状态", "提示词", "模型", "尺寸", "创建时间"],
                datatype=["str", "str", "str", "str", "str", "str", "str"],
                value=app.get_task_history(),
                label="任务列表",
                interactive=True
            )
            
            with gr.Row():
                select_all_btn = gr.Button("☑️ 全选", variant="secondary")
                deselect_all_btn = gr.Button("⬜ 取消全选", variant="secondary")
                download_all_btn = gr.Button("📥 一键下载", variant="primary")
            
            download_status = gr.Textbox(label="下载状态", lines=3)
            
            with gr.Row():
                gr.Markdown("### 查询任务")
            with gr.Row():
                queue_vendor = gr.Dropdown(choices=app.get_enabled_vendors(), label="选择厂商", value=app.get_enabled_vendors()[0] if app.get_enabled_vendors() else None)
                queue_task_id = gr.Textbox(label="Task ID", placeholder="点击上方Task ID复制后粘贴...")
                queue_query_btn = gr.Button("🔍 查询")
            
            with gr.Row():
                queue_result_img = gr.Image(label="结果")
                queue_result_status = gr.Textbox(label="状态", lines=3)
            
            def on_select_all(current_data):
                if current_data is None:
                    return "", "列表为空"
                
                task_ids = []
                
                import pandas as pd
                if isinstance(current_data, pd.DataFrame):
                    for idx, row in current_data.iterrows():
                        task_id = str(row[0]).strip()
                        if task_id and len(task_id) > 5:
                            task_ids.append(task_id)
                else:
                    for row in current_data:
                        if isinstance(row, (list, tuple)) and len(row) >= 1:
                            task_id = str(row[0]).strip()
                            if task_id and len(task_id) > 5 and task_id not in ["Task ID", "类型", "状态", "提示词", "模型", "尺寸", "创建时间"]:
                                task_ids.append(task_id)
                
                if not task_ids:
                    return "", "无有效任务ID"
                return ",".join(task_ids), f"已选择 {len(task_ids)} 个任务"
            
            def on_deselect_all():
                return "", "已取消全选"
            
            select_all_btn.click(on_select_all, task_list, [queue_task_id, download_status])
            deselect_all_btn.click(on_deselect_all, None, [queue_task_id, download_status])
            download_all_btn.click(app.download_all_tasks, [queue_vendor, queue_task_id], download_status)
            refresh_history_btn.click(lambda t: app.get_task_history(t), filter_type, task_list)
            filter_type.change(lambda t: app.get_task_history(t), filter_type, task_list)
            queue_query_btn.click(app.query_task, [queue_vendor, queue_task_id], [queue_result_status, queue_result_img])
        
        with gr.Tab("ℹ️ 关于"):
            gr.Markdown("""
            ### 🎨 白嫖大师 - 通用AI客户端
            
            **版本**: 2.0.0
            
            **功能特点**:
            - 支持多厂商接入 (Moark, OpenAI, 硅基流动, 阿里云等)
            - 文生图、图像编辑功能
            - 异步视频生成功能
            - 预设厂商模板，一键添加
            - 统一的任务管理
            
            **使用说明**:
            1. 在"厂商管理"页面添加厂商（可使用预设模板）
            2. 填写 API Key
            3. 选择厂商和模型
            4. 输入提示词生成内容
            
            **作者**: ops120
            """)
    
    gr.Markdown("---")
    gr.Markdown("*© 2024 白嫖大师 - 让AI不再昂贵*")

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=11111, share=False)
