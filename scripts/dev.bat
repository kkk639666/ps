@echo off
REM 番茄病虫害识别系统 — Windows CMD 一键启动脚本
REM 用法: scripts\dev.bat
REM      scripts\dev.bat backend    (仅后端)
REM      scripts\dev.bat frontend   (仅前端)

setlocal enabledelayedexpansion

set "ROOT=%~dp0.."
set "BACKEND=%ROOT%\web\backend"
set "FRONTEND=%ROOT%\web\frontend"
set "MODE=%~1"

echo.
echo ========================================
echo   番茄病虫害识别系统 — 开发服务启动
echo ========================================

REM ── Backend ──────────────────────────────
if /I not "%MODE%"=="frontend" (
    echo.
    echo [后端] 检查依赖...
    pip install -r "%BACKEND%\requirements.txt"
    if errorlevel 1 (
        echo [错误] pip install 失败，请检查 Python 环境
        exit /b 1
    )

    if not exist "%BACKEND%\.env" (
        copy "%BACKEND%\.env.example" "%BACKEND%\.env" >nul
        echo [后端] 已创建 .env（从 .env.example 复制）
    )

    echo [后端] 在新窗口启动 FastAPI ^(端口 8000^)...
    start "FastAPI Backend" cmd /k "cd /d "%BACKEND%" && python main.py"
    echo [后端] http://localhost:8000  ^(API 文档: http://localhost:8000/docs^)
)

REM ── Frontend ─────────────────────────────
if /I not "%MODE%"=="backend" (
    echo.
    if not exist "%FRONTEND%\node_modules" (
        echo [前端] 安装 npm 依赖（首次运行，请稍候…^)
        pushd "%FRONTEND%"
        npm install
        popd
    )

    echo [前端] 在新窗口启动 Vite ^(端口 5173^)...
    start "Vite Frontend" cmd /k "cd /d "%FRONTEND%" && npm run dev"
    echo [前端] http://localhost:5173
)

echo.
echo ========================================
echo   启动完成！按任意键退出此脚本
echo   （后端/前端窗口将继续运行）
echo ========================================
pause >nul
