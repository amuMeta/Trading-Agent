@echo off
chcp 65001 >nul 2>&1
title TradingAgents 启动器

echo ========================================
echo   TradingAgents 多服务启动器
echo ========================================
echo.

 REM 颜色定义
set "GREEN=\033[32m"
set "RED=\033[31m"
set "YELLOW=\033[33m"
set "RESET=\033[0m"

echo 检查环境...

 REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)
echo [OK] Python已安装

 REM 检查.env文件
if not exist ".env" (
    echo [警告] .env文件不存在，正在创建...
    copy NUL .env >nul 2>&1
)

 REM 检查MCP配置
if not exist "mcp_config.json" (
    echo [警告] mcp_config.json不存在
)

echo.
echo ========================================
echo   选择启动模式:
echo ========================================
echo   1. Streamlit Web界面 (推荐)
echo   2. React前端 + API后端
echo   3. 仅API后端
echo   4. 仅MCP服务
echo   0. 退出
echo.
set /p mode=请输入选项 [1-4]:

if "%mode%"=="1" goto streamlit
if "%mode%"=="2" goto react
if "%mode%"=="3" goto api
if "%mode%"=="4" goto mcp
if "%mode%"=="0" exit /b 0

echo [错误] 无效选项
pause
exit /b 1

:streamlit
echo.
echo 启动Streamlit Web界面...
echo 访问地址: http://localhost:8501
echo.
python -m streamlit run web_app.py
pause
exit /b 0

:react
echo.
echo [1/2] 启动API后端...
start "TradingAgents API" cmd /k "python run_api.py"
timeout /t 3 /nobreak >nul

echo [2/2] 启动React前端...
start "TradingAgents React" cmd /k "cd frontend ^&^& npm run dev"
echo.
echo 启动完成!
echo - API后端: http://localhost:8000
echo - React前端: http://localhost:3000
echo.
pause
exit /b 0

:api
echo.
echo 启动API后端...
echo 访问地址: http://localhost:8000
echo.
python run_api.py
pause
exit /b 0

:mcp
echo.
echo 启动MCP服务...
echo 访问地址: http://127.0.0.1:9898
echo.
echo [提示] 请确保MCP服务器已启动
echo [提示] 如果未启动，请使用 npx @modelcontextserver/server 或其他MCP服务
timeout /t 5 /nobreak >nul
exit /b 0