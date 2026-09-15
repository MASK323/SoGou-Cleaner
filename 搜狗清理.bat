@echo off
title 搜狗输入法 清理工具
cd /d "%~dp0"

rem ===== 管理员权限检查: 不足则通过 UAC 自提权重启 =====
net session >nul 2>&1
if errorlevel 1 (
    echo.
    echo   正在请求管理员权限, 请在弹窗中点击 [是] ...
    echo.
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

rem ===== 定位 Python =====
set "PY="
where py >nul 2>&1
if not errorlevel 1 set "PY=py"
if not defined PY (
    where python >nul 2>&1
    if not errorlevel 1 set "PY=python"
)
if not defined PY (
    echo.
    echo   未找到 Python。请先安装 Python 并加入 PATH。
    echo.
    pause
    exit /b 1
)

rem ===== 启动交互菜单 =====
%PY% "%~dp0sogou_cleaner.py"
set RC=%errorlevel%

echo.
if not "%RC%"=="0" echo   退出码: %RC%
pause
exit /b %RC%
