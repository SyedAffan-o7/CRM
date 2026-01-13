@echo off
echo Setting up Django CRM System...
echo.

echo Installing required packages...
pip install django==4.2.7 djangorestframework==3.14.0 pillow==10.0.1

echo.
echo Creating database migrations...
python manage.py makemigrations

echo.
echo Applying migrations...
python manage.py migrate

echo.
echo Creating superuser (admin/admin123)...
echo from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin123') | python manage.py shell

echo.
echo Starting Django development server...
echo CRM will be available at: http://127.0.0.1:8000/
echo Admin panel at: http://127.0.0.1:8000/admin/
echo Login: admin / admin123
echo.
python manage.py runserver
