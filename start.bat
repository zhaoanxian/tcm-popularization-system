@echo off
chcp 936 >nul
title ��ҽҩ����ϵͳ - һ������
color 07
cd /d "%~dp0"

echo ==================================================
echo    ��ҽҩ������������ѯ����ϵͳ
echo    һ������
echo ==================================================
echo.

rem ---------- 1. ȷ���Լ�����Ŀ��Ŀ¼ ----------
if not exist "manage.py" (
    echo [����] ��ǰĿ¼û�� manage.py
    echo.
    echo ��� start.bat ������Ŀ��Ŀ¼���� manage.py ͬһ�㡣
    echo ��ǰĿ¼��%~dp0
    echo.
    pause
    exit /b 1
)

rem ---------- 2. �� Python ----------
set "PY="
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if not defined PY if exist "venv\Scripts\python.exe" set "PY=venv\Scripts\python.exe"
if not defined PY (
    where python >nul 2>nul
    if not errorlevel 1 set "PY=python"
)
if not defined PY (
    echo [����] �Ҳ��� Python
    echo.
    echo ���Ȱ�װ Python 3.10 ����߰汾����װʱ��ѡ "Add Python to PATH"��
    echo ��������Ŀ��Ŀ¼ִ�У�python -m venv .venv
    echo.
    pause
    exit /b 1
)
echo [OK] Python��%PY%

rem ---------- 3. ������� ----------
"%PY%" -c "import django" >nul 2>nul
if errorlevel 1 (
    echo [��ʾ] ȱ�� Django�����ڰ�װ��������һ�ο���Ҫ������...
    "%PY%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [����] ������װʧ�ܣ����ֶ�ִ�У�
        echo     "%PY%" -m pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
    echo [OK] ������װ���
)

rem ---------- 4. �״����н��� ----------
if not exist "db.sqlite3" (
    echo [��ʾ] û�����ݿ⣬���ڳ�ʼ��...
    "%PY%" manage.py migrate
    "%PY%" manage.py seed_data >nul 2>nul
    echo [OK] ���ݿ�������
)

rem ---------- 5. �˿� ----------
netstat -ano | findstr "LISTENING" | findstr ":8000" >nul
if not errorlevel 1 (
    echo [��ʾ] 8000 �˿��Ѿ��ڼ���������ϵͳ�Ѿ������ˡ�
    echo        ֱ�Ӵ��������http://127.0.0.1:8000/
    echo.
    start "" http://127.0.0.1:8000/
    pause
    exit /b 0
)

echo.
echo ==================================================
echo    ����������3 ����Զ��������
echo.
echo    ��ַ��http://127.0.0.1:8000/
echo.
echo    ��ʾ�˺ţ����붼�� tcm123456��
echo        admin01    ϵͳ����Ա
echo        editor01   ���ձ༭
echo        doctor01   ��ѯҽʦ
echo        user01     ��ͨ�û�
echo.
echo    [��Ҫ] ����ڴ��ڲ�Ҫ�أ��ص���վ��ֹͣ
echo ==================================================
echo.

start "" /b cmd /c "ping -n 4 127.0.0.1 >nul & start http://127.0.0.1:8000/"

"%PY%" manage.py runserver 0.0.0.0:8000

echo.
echo ==================================================
echo   ������ֹͣ����������رմ���
echo ==================================================
pause
