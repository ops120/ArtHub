# 🎨 白嫖大师 - 图像视频生成工具

> 让 AI 不再昂贵，让创意不受限制  
> 作者：**你们喜爱的老王** | [B 站主页](https://space.bilibili.com/97727630)

## ✨ 功能特性

### 📝 基础图像功能
- **文生图**：纯文本生成图像，支持多种模型
- **图像编辑**：上传图片进行编辑，支持蒙版功能
- **URL 参考图**：通过图片 URL 生成参考图

### 🎬 视频生成功能 (NEW!)
- **异步文生视频**：文本直接生成视频
  - 支持模型：stepvideo-t2v、Wan2.1-T2V-1.3B
  - 默认时长：5秒（可调整）
  - 支持视频预览和下载
  
- **异步图生视频**：图片生成视频
  - 支持模型：LTX-2
  - 默认时长：5秒（可调整）
  - 支持图片上传和视频预览

> 💡 **查看最新支持模型**：[Moark API 文档](https://moark.com/docs/openapi/v1#tag/%E5%9B%BE%E5%83%8F%E7%94%9F%E6%88%90/post/async/images/generations)

### ⏳ 异步功能
- **异步文生图**：避免超时，适合复杂图像生成
  - 支持模型：FLUX.1-dev、LongCat-Image、flux-1-schnell、Qwen-Image-2512、Z-Image、Qwen-Image
  - 提交后立即返回 Task ID
  - 支持状态轮询查询
  
- **异步图像编辑**：避免超时，适合复杂编辑任务
  - 支持模型：LongCat-Image-Edit、Qwen-Image-Edit-2511、FLUX.1-Kontext-dev
  - 支持蒙版 (mask) 功能
  - 提交后获取 Task ID，可随时查询进度

### 📋 任务队列管理
- **任务历史记录**：所有异步任务自动保存
- **按日期筛选**：快速定位特定日期的任务
- **按类型筛选**：文生图/图像编辑/文生视频/图生视频分类查看
- **批量查询**：同时查询多个任务状态，支持视频任务识别
- **批量下载**：一键下载选中任务，自动按日期归档

### 🗄️ 数据存储
- **SQLite 持久化**：使用 SQLite 数据库存储任务历史
- **自动归档**：下载文件自动保存到 `outputs/{日期}/` 目录
- **智能格式识别**：图像保存为 PNG，视频保存为 MP4
- **路径记录**：数据库记录每个任务的下载路径

### 🎯 异步功能优势
1. **避免超时**：提交任务后立即返回，无需长时间等待
2. **支持轮询**：可随时查询任务状态和进度
3. **适合复杂任务**：特别适合高分辨率、复杂场景的生成
4. **结果可靠**：任务完成后结果保存 1 天，及时下载即可
5. **批量管理**：支持多选、批量查询和下载

## 🚀 快速开始

### 方式一：CMD 启动脚本 (推荐)
```cmd
启动.cmd
```

### 方式二：手动启动
```cmd
cd /d "%~dp0"
python moark_image_edit_ui.py
```

访问：http://localhost:11111

### 环境要求
- Python 3.8+
- Windows CMD (不支持 PowerShell)
- 支持中文路径和空格路径

## 📋 配置说明

首次启动需要配置 API Key:

### 配置文件位置
配置文件位于 `conf/moark_config.json`

### 配置方式
**方式一：配置页面 (推荐)**
1. 启动应用后进入"⚙️ 配置"标签页
2. 填写配置信息
3. 点击保存（配置实时生效，无需重启）

**方式二：直接编辑配置文件**
编辑 `conf/moark_config.json`:
```json
{
  "base_url": "https://api.moark.com/v1",
  "api_key": "your-api-key-here",
  "text2img_model": "z-image-turbo",
  "edit_model": "Qwen-Image-Edit",
  "timeout": 180,
  "default_size": "1024x1024",
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
    "stepvideo-t2v",
    "Wan2.1-T2V-1.3B"
  ],
  "async_img2vid_models": [
    "LTX-2",
    "LongCat-Video"
  ]
}
```

## 🎬 视频生成使用指南

### 文生视频
1. 进入"🎬 异步文生视频"标签页
2. 输入提示词（prompt）
3. 选择视频模型
4. 点击"📤 提交异步任务"
5. 使用 Task ID 查询进度
6. 完成后可预览和下载视频

### 图生视频
1. 进入"🎥 异步图生视频"标签页
2. 上传图片或输入图片 URL
3. 输入提示词（可选）
4. 选择视频模型
5. 点击"📤 提交异步任务"
6. 使用 Task ID 查询进度
7. 完成后可预览和下载视频

### 视频参数说明
- **时长**：默认 5 秒，可通过 API 参数调整
- **格式**：生成 MP4 格式视频
- **分辨率**：根据模型支持的分辨率自动调整

## 📁 项目结构

```
白嫖大师/
├── moark_image_edit_ui.py     # 主程序文件
├── 启动.cmd                   # Windows 启动脚本
├── requirements.txt           # Python 依赖
├── README.md                  # 项目说明
├── conf/                      # 配置文件目录
│   └── moark_config.json      # API 配置
├── outputs/                   # 输出文件目录（自动创建）
│   └── 2024-03-05/           # 按日期归档
│       ├── txt2img_xxx.png
│       ├── edit_xxx.png
│       ├── txt2vid_xxx.mp4
│       └── img2vid_xxx.mp4
└── tasks.db                  # SQLite 数据库（自动创建）
```

## 🔧 安装依赖

```bash
pip install -r requirements.txt
```

### 主要依赖
- gradio==3.50.2
- requests
- pillow
- sqlite3

## 🐛 常见问题

### Q: 启动时报错 "ModuleNotFoundError: No module named 'gradio'"
A: 请先安装依赖：`pip install -r requirements.txt`

### Q: 视频任务查询失败，显示 "cannot identify image file"
A: 这是正常现象，视频任务返回的是视频文件而非图像，系统已正确处理

### Q: 配置保存后下拉框选项没有更新
A: 配置保存后会自动更新所有下拉框选项，无需重启应用

### Q: 批量下载时文件格式不对
A: 系统会根据任务类型自动识别格式：图像保存为 PNG，视频保存为 MP4

## 📄 许可证

本项目仅供学习和研究使用，请遵守相关法律法规。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**温馨提示**：请合理使用 API，避免过度调用导致费用增加。