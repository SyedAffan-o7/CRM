# Django CRM Deployment Guide for Render

This guide will help you deploy the Django CRM system to Render.com successfully.

## Prerequisites

1. **GitHub Account**: Your code must be in a GitHub repository
2. **Render Account**: Sign up at [render.com](https://render.com)
3. **Git**: Ensure your project is committed and pushed to GitHub

## Deployment Steps

### Step 1: Prepare Your Repository

1. **Commit all changes** to your GitHub repository:
   ```bash
   git add .
   git commit -m "Prepare for Render deployment"
   git push origin main
   ```

### Step 2: Deploy to Render

1. **Login to Render**: Go to [render.com](https://render.com) and sign in
2. **Create New Web Service**: Click "New" → "Web Service"
3. **Connect Repository**: Connect your GitHub account and select this repository
4. **Configure Service**:
   - **Name**: `aaa-crm-system` (or your preferred name)
   - **Environment**: `Python 3`
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn crm_project.wsgi:application`
   - **Plan**: Select "Free" for testing

### Step 3: Environment Variables

In the Render dashboard, add these environment variables:

**Required Variables:**
- `PYTHON_VERSION`: `3.11.0`
- `DEBUG`: `False`
- `ALLOWED_HOSTS`: `.onrender.com`
- `DB_SSL_REQUIRED`: `True`

**Auto-Generated Variables:**
- `DATABASE_URL`: Will be automatically provided when you add a database
- `SECRET_KEY`: Click "Generate" to create a secure secret key

### Step 4: Add Database

1. **Create PostgreSQL Database**:
   - In Render dashboard, click "New" → "PostgreSQL"
   - **Name**: `aaa-crm-db`
   - **Plan**: Select "Free"
   
2. **Connect Database to Web Service**:
   - Go to your web service settings
   - In Environment Variables, add:
     - `DATABASE_URL`: Select "From Database" → Choose your database

### Step 5: Deploy

1. **Trigger Deployment**: Click "Deploy Latest Commit"
2. **Monitor Logs**: Watch the build process in the logs
3. **Wait for Completion**: First deployment may take 5-10 minutes

## Post-Deployment Setup

### Access Your Application

1. **Get URL**: Your app will be available at `https://your-service-name.onrender.com`
2. **Login**: Use the default superuser credentials:
   - Username: `admin`
   - Password: `admin123`
   - **⚠️ IMPORTANT**: Change these credentials immediately after first login!

### Initial Configuration

1. **Access Admin Panel**: Go to `/admin/` to configure the system
2. **Create Roles**: The deployment script automatically creates default roles
3. **Add Users**: Create additional users through Settings → User Management
4. **Configure System**: Set up products, categories, and other master data

## Troubleshooting

### Common Issues

1. **Build Fails**:
   - Check that `requirements.txt` includes all dependencies
   - Ensure `build.sh` has execute permissions
   - Review build logs for specific errors

2. **Database Connection Issues**:
   - Verify `DATABASE_URL` environment variable is set
   - Check that database service is running
   - Ensure `DB_SSL_REQUIRED=True` for production

3. **Static Files Not Loading**:
   - Verify WhiteNoise is in `MIDDLEWARE`
   - Check `STATIC_ROOT` and `STATICFILES_STORAGE` settings
   - Run `python manage.py collectstatic` manually if needed

4. **Permission Errors**:
   - Ensure default roles are created during deployment
   - Check that superuser has proper profile and role assigned

### Useful Commands

**View Logs**:
```bash
# In Render dashboard, go to your service → Logs
```

**Manual Commands** (via Render Shell):
```bash
# Create superuser
python manage.py createsuperuser

# Initialize roles
python manage.py init_roles

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate
```

## Security Considerations

1. **Change Default Credentials**: Immediately change the default admin password
2. **Environment Variables**: Never commit sensitive data to the repository
3. **HTTPS**: Render provides HTTPS by default
4. **Database**: Use strong database passwords
5. **Secret Key**: Use the auto-generated secret key, never use the default one

## Performance Optimization

1. **Database Indexing**: Ensure proper database indexes are in place
2. **Static Files**: WhiteNoise handles static file serving efficiently
3. **Caching**: Consider adding Redis for session/cache storage for better performance
4. **Media Files**: For production, consider using cloud storage for uploaded files

## Monitoring

1. **Render Metrics**: Monitor CPU, memory, and response times in Render dashboard
2. **Application Logs**: Check Django logs for errors and performance issues
3. **Database Performance**: Monitor database queries and optimize slow queries

## Backup Strategy

1. **Database Backups**: Render provides automatic database backups
2. **Code Backups**: Ensure your GitHub repository is your source of truth
3. **Media Files**: Implement a backup strategy for uploaded files

## Support

- **Render Documentation**: [render.com/docs](https://render.com/docs)
- **Django Documentation**: [docs.djangoproject.com](https://docs.djangoproject.com)
- **Project Issues**: Create issues in your GitHub repository

---

**🚀 Your Django CRM system is now ready for production deployment on Render!**
