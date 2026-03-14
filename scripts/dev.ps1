# 番茄病虫害识别系统 — 开发服务启动脚本 (scripts/ 版本)
# 用法: scripts\dev.ps1
#       scripts\dev.ps1 -Backend    (仅后端)
#       scripts\dev.ps1 -Frontend   (仅前端)
#
# 注意: 根目录下的 start.ps1 提供相同功能，可直接使用 .\start.ps1

param(
    [switch]$Backend,
    [switch]$Frontend
)

$Root = (Get-Item $PSScriptRoot).Parent.FullName
& "$Root\start.ps1" `
    -BackendOnly:($Backend -and -not $Frontend) `
    -FrontendOnly:($Frontend -and -not $Backend)
