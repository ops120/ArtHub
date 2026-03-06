@echo off
chcp 65001 >nul
echo ============================================
echo   白嫖大师 - 图像视频生成工具
echo   启动脚本 (CMD 版本)
echo ============================================
echo.

REM 获取脚本所在目录
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo [信息] 工作目录: %CD%
echo.

REM 检查 Python 是否安装
echo [信息] 检查 Python...
where python >nul 2>&1
if errorlevel 1 (
    echo.
    echo [错误] 未检测到 Python，请先安装 Python
    echo.
    echo 请从以下地址下载并安装 Python:
    echo https://www.python.org/downloads/
    echo.
    echo 安装步骤：
    echo 1. 下载 Python 3.8+ 版本
    echo 2. 运行安装程序
    echo 3. 勾选 "Add Python to PATH"
    echo 4. 选择 "Install Now"
    echo.
    echo 安装完成后重新运行此脚本
    echo.
    pause
    exit /b 1
)

REM 显示 Python 版本
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [信息] Python 版本: %PYTHON_VERSION%
echo.

REM 启用延迟扩展
setlocal enabledelayedexpansion

REM 检查端口 11111 是否被占用
echo [信息] 检查端口 11111 是否被占用...
netstat -ano | findstr ":11111" >nul
if not errorlevel 1 (
    echo [警告] 端口 11111 已被占用，正在查找并终止相关进程...
    
    REM 查找占用端口 11111 的进程
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":11111" ^| findstr "LISTENING"') do (
        set PID=%%a
        echo [信息] 找到占用端口的进程 PID: !PID!
        
        REM 终止进程
        taskkill /f /pid !PID! >nul 2>&1
        if errorlevel 1 (
            echo [警告] 无法终止进程 PID: !PID!，可能需要管理员权限
        ) else (
            echo [信息] 已终止进程 PID: !PID!
        )
    )
    echo.
)

REM 检查是否已有 Python 进程在运行
echo [信息] 检查是否已有服务在运行...
wmic process where "name='python.exe' and commandline like '%%moark_image_edit_ui.py%%'" get processid 2>nul | findstr /r "^[0-9][0-9]*" >nul
if not errorlevel 1 (
    echo [警告] 检测到已有服务在运行，正在终止...
    
    REM 终止所有相关的 Python 进程
    for /f "tokens=1" %%a in ('wmic process where "name='python.exe' and commandline like '%%moark_image_edit_ui.py%%'" get processid ^| findstr /r "^[0-9][0-9]*"') do (
        echo [信息] 终止进程 PID: %%a
        taskkill /f /pid %%a >nul 2>&1
    )
    
    REM 等待进程完全退出
    timeout /t 2 /nobreak >nul
    echo.
)

echo [信息] 正在检查依赖...
echo.

REM 配置 pip 使用清华源
set PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
set PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

REM 使用 requirements.txt 安装依赖
echo [信息] 正在安装依赖（使用清华源）...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo.
    echo [警告] 依赖安装可能有问题，请检查网络连接
    echo.
)

echo.
echo [信息] 依赖检查完成
echo.
echo [信息] 正在创建必要目录...
echo.

REM 创建必要的目录 (如果不存在)
if not exist "logs" mkdir "logs"
if not exist "outputs" mkdir "outputs"
if not exist "templates" mkdir "templates"
if not exist "docs" mkdir "docs"
if not exist "conf" mkdir "conf"

echo [信息] 目录创建完成
echo.
echo [信息] 检查配置文件...
echo.

REM 检查并复制配置文件
if not exist "conf\moark_config.json" (
    if exist "conf\moark_config.example.json" (
        echo [信息] 复制配置文件...
        copy "conf\moark_config.example.json" "conf\moark_config.json" >nul
        echo [信息] 配置文件已创建，请编辑 conf\moark_config.json 填入你的 API Key
        echo.
    ) else (
        echo [错误] 缺少配置文件 conf\moark_config.example.json
        echo.
        pause
        exit /b 1
    )
)

echo.
echo ============================================
echo   正在启动图像视频生成工具...
echo ============================================
echo [信息] 服务地址：http://localhost:11111
echo [信息] 日志目录：logs\
echo [信息] 输出目录：outputs\
echo [信息] 配置目录：conf\
echo ============================================
echo.
echo 提示：按 Ctrl+C 可以停止服务
echo.

REM 启动应用
python moark_image_edit_ui.py

if errorlevel 1 (
    echo.
    echo [错误] 程序异常退出，错误代码: %errorlevel%
    echo.
)

echo.
echo [信息] 服务已停止
echo.
pause