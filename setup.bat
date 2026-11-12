@echo off
echo Math Table Checker - Django Setup
echo =================================

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install requirements
echo Installing requirements...
pip install -r requirements.txt

REM Check if .env exists
if not exist ".env" (
    echo Creating .env file from template...
    copy .env.example .env
    echo Please edit .env file and add your Gemini API key!
)

REM Run migrations
echo Running database migrations...
python manage.py makemigrations
python manage.py migrate

REM Collect static files
echo Collecting static files...
python manage.py collectstatic --noinput

echo.
echo Setup complete!
echo 1. Edit .env file and add your Gemini API key
echo 2. Run: python manage.py runserver
echo 3. Open: http://127.0.0.1:8000/
echo.
echo Optional: Create admin user with "python manage.py createsuperuser"
pause
