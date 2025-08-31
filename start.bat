@echo off
echo Starting SmartBookkeeper...
echo.

REM 检查虚拟环境是否存在
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM 激活虚拟环境
echo Activating virtual environment...
call venv\Scripts\activate

REM 安装依赖
echo Installing dependencies...
pip install -r requirements.txt

REM 检查.env文件是否存在
if not exist ".env" (
    echo Creating .env file from .env.example...
    copy .env.example .env
    echo Please edit .env file with your configuration before running the application.
    echo.
    pause
    exit /b
)

REM 运行应用
echo Starting application...
echo Application will be available at http://localhost:8000
echo API documentation available at http://localhost:8000/docs
echo.
python -m uvicorn app.main:app --reload

pause