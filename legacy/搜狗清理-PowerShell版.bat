@echo off
title 搜狗输入法 清理工具 ^(PowerShell 版^)
cd /d "%~dp0"

rem ===== 管理员权限检查: 不足则通过 UAC 自提权重启 =====
net session >nul 2>&1
if errorlevel 1 (
    echo.
    echo   正在请求管理员权限, 请在弹窗中点击 [是] ...
    echo.
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs -ArgumentList '%*'"
    exit /b
)

rem ===== 解除"网络来源"标记, 避免执行策略拦截 =====
powershell -NoProfile -Command "Get-ChildItem -LiteralPath '%~dp0' -Filter *.ps1 -ErrorAction SilentlyContinue | Unblock-File" >nul 2>&1

rem ===== 定位 PowerShell (优先 Windows PowerShell 5.1) =====
set "PS="
where powershell >nul 2>&1
if not errorlevel 1 set "PS=powershell"
if not defined PS (
    where pwsh >nul 2>&1
    if not errorlevel 1 set "PS=pwsh"
)
if not defined PS (
    echo.
    echo   未找到 PowerShell。
    echo.
    pause
    exit /b 1
)

rem ===== 启动: Bypass 绕过执行策略, 避免"脚本被禁用"直接闪退 =====
"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0sogou-debloat.ps1" %*
set RC=%errorlevel%

echo.
if not "%RC%"=="0" echo   退出码: %RC%
pause
exit /b %RC%
