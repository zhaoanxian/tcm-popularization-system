@echo off
chcp 936 >nul
title 中医药科普系统 - 一键启动
color 07
cd /d "%~dp0"

echo ==================================================
echo    中医药科普内容与咨询管理系统
echo    一键启动
echo ==================================================
echo.

rem ---------- 1. 确认自己在项目根目录 ----------
if not exist "manage.py" (
    echo [错误] 当前目录没有 manage.py
    echo.
    echo 请把 start.bat 放在项目根目录，和 manage.py 同一层。
    echo 当前目录：%~dp0
    echo.
    pause
    exit /b 1
)

rem ---------- 2. 找 Python ----------
set "PY="
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if not defined PY if exist "venv\Scripts\python.exe" set "PY=venv\Scripts\python.exe"
if not defined PY (
    where python >nul 2>nul
    if not errorlevel 1 set "PY=python"
)
if not defined PY (
    echo [错误] 找不到 Python
    echo.
    echo 请先安装 Python 3.10 或更高版本，安装时勾选 "Add Python to PATH"。
    echo 或者在项目根目录执行：python -m venv .venv
    echo.
    pause
    exit /b 1
)
echo [OK] Python：%PY%

rem ---------- 3. 检查依赖 ----------
"%PY%" -c "import django" >nul 2>nul
if errorlevel 1 (
    echo [提示] 缺少 Django，正在安装依赖，第一次可能要几分钟...
    "%PY%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [错误] 依赖安装失败，请手动执行：
        echo     "%PY%" -m pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
    echo [OK] 依赖安装完成
)

rem ---------- 4. 首次运行建库 ----------
if not exist "db.sqlite3" (
    echo [提示] 没有数据库，正在初始化...
    "%PY%" manage.py migrate
    "%PY%" manage.py seed_data >nul 2>nul
    echo [OK] 数据库已生成
)

rem ---------- 5. 端口 ----------
netstat -ano | findstr "LISTENING" | findstr ":8000" >nul
if not errorlevel 1 (
    echo [提示] 8000 端口已经在监听，可能系统已经开着了。
    echo        直接打开浏览器：http://127.0.0.1:8000/
    echo.
    start "" http://127.0.0.1:8000/
    pause
    exit /b 0
)

echo.
echo ==================================================
echo    正在启动，3 秒后自动打开浏览器
echo.
echo    地址：http://127.0.0.1:8000/
echo.
echo    演示账号（密码都是 tcm123456）
echo        admin01    系统管理员
echo        editor01   科普编辑
echo        doctor01   咨询医师
echo        user01     普通用户
echo.
echo    >>> 这个黑窗口不要关，关掉网站就停止 <<<
echo ==================================================
echo.

start "" /b cmd /c "ping -n 4 127.0.0.1 >nul & start http://127.0.0.1:8000/"

"%PY%" manage.py runserver 0.0.0.0:8000

echo.
echo ==================================================
echo   服务已停止，按任意键关闭窗口
echo ==================================================
pause
