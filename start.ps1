# 番茄病虫害识别系统 — Windows 一键启动脚本
# 用法: 在 PowerShell 中运行 .\start.ps1
# 或只启动后端: .\start.ps1 -BackendOnly
# 或只启动前端: .\start.ps1 -FrontendOnly

param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

function Write-Header($msg) {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "  $msg" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
}

# ── Backend ──────────────────────────────────────────────────────────────────
if (-not $FrontendOnly) {
    Write-Header "启动后端 (FastAPI — port 8000)"
    $backendDir = Join-Path $Root "web\backend"

    # Copy .env if missing
    $envFile = Join-Path $backendDir ".env"
    $envExample = Join-Path $backendDir ".env.example"
    if (-not (Test-Path $envFile)) {
        Copy-Item $envExample $envFile
        Write-Host "  已创建 .env（从 .env.example 复制）" -ForegroundColor Yellow
    }

    # Install backend deps
    Write-Host "  安装后端依赖..." -ForegroundColor Gray
    pip install -r (Join-Path $backendDir "requirements.txt") -q
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[错误] pip install 失败，请检查 Python 环境" -ForegroundColor Red
        exit 1
    }

    # Start backend in a new window
    $backendCmd = "cd `"$backendDir`"; python main.py"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd -WindowStyle Normal
    Write-Host "  后端已在新窗口启动 → http://localhost:8000" -ForegroundColor Green
    Write-Host "  API 文档 → http://localhost:8000/docs" -ForegroundColor Green
}

# ── Frontend ─────────────────────────────────────────────────────────────────
if (-not $BackendOnly) {
    Write-Header "启动前端 (Vite — port 5173)"
    $frontendDir = Join-Path $Root "web\frontend"

    # Install frontend deps if needed
    if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
        Write-Host "  安装前端依赖（首次运行，请稍候…）" -ForegroundColor Gray
        $npmCmd = "cd `"$frontendDir`"; npm install"
        Invoke-Expression $npmCmd
    }

    # Start frontend in a new window
    $frontendCmd = "cd `"$frontendDir`"; npm run dev"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd -WindowStyle Normal
    Write-Host "  前端已在新窗口启动 → http://localhost:5173" -ForegroundColor Green
}

Write-Header "启动完成"
Write-Host "  前端地址: http://localhost:5173" -ForegroundColor White
Write-Host "  后端 API: http://localhost:8000/api" -ForegroundColor White
Write-Host "  API 文档: http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "按 Ctrl+C 或关闭对应窗口以停止服务`n" -ForegroundColor Gray
