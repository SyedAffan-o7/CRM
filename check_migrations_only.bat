@echo off
echo Checking for pending migrations...
echo.

echo Creating migrations for any model changes...
python manage.py makemigrations

echo.
echo Applying migrations...
python manage.py migrate

echo.
echo Migration check complete!
