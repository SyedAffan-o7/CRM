# Django CRM System

A comprehensive, phone-focused CRM system designed for small sales teams with relationship management and product tracking capabilities.

## Features

### Core Modules
- **Enquiries Management**: Track potential customers with contact info, status, priority, and sales assignments
- **Product Management**: Master product catalog with multi-select functionality for enquiries
- **Contacts Management**: Maintain detailed contact records with phone numbers, WhatsApp, and company associations
- **Accounts Management**: Manage company/account information with industry types and status tracking
- **Deals Management**: Track sales opportunities through different stages with value and probability tracking
- **Activities Log**: Record all interactions (calls, emails, meetings, notes) with automatic timestamping

### Relationship Management
- **Lead → Contact Conversion**: Convert enquiries to contacts with optional account and deal creation
- **Contact ↔ Account Relationships**: Multiple contacts per account with automatic linking
- **Deal Requirements**: Deals must have contacts, accounts are optional
- **Product Selection**: Multi-select product enquiries with master product catalog

### Key Capabilities
- Phone number-focused design (primary field in all modules)
- Simple, user-friendly interface built with Bootstrap
- Dashboard with key metrics and recent activities
- Search and filtering across all modules
- Activity tracking for all customer interactions
- Admin panel for advanced management

## Technology Stack
- **Backend**: Django 4.2.7 (Python)
- **Database**: SQLite (development) / PostgreSQL (production ready)
- **Frontend**: HTML5, CSS3, JavaScript with Django templates
- **UI Framework**: Bootstrap 5.3 for responsive design
- **Icons**: Bootstrap Icons

## Quick Setup

### Prerequisites
- Python 3.8+
- pip (Python package manager)

### Installation Steps

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up Database**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

3. **Create Admin User**
   ```bash
   python manage.py createsuperuser
   ```
   - Username: admin
   - Email: admin@yourcompany.com
   - Password: (choose a secure password)

4. **Run the Server**
   ```bash
   python manage.py runserver
   ```

5. **Access the Application**
   - Main CRM: http://127.0.0.1:8000/
   - Admin Panel: http://127.0.0.1:8000/admin/

## User Roles

### Super Admin
- Full access to all modules
- Dashboard with analytics and metrics
- User management capabilities
- System configuration access

### Sales Team
- Lead entry and tracking
- Contact and account management
- Deal pipeline management
- Activity logging

## Default Login
- Username: `admin`
- Password: `admin123` (change immediately after first login)

## Usage Guide

### Adding Your First Lead
1. Navigate to "Leads" in the sidebar
2. Click "Add New Lead"
3. Fill in contact name and phone number (required)
4. Add company, products of interest, and priority
5. Assign to a sales person
6. Save the lead

### Managing Contacts
1. Go to "Contacts" section
2. Add contacts with full details including WhatsApp numbers
3. Associate contacts with companies/accounts
4. Track all interactions through activities

### Tracking Deals
1. Create deals from qualified leads
2. Set deal values and probability percentages
3. Track through sales stages: Prospecting → Proposal → Negotiation → Closed
4. Log reasons for wins/losses

### Logging Activities
1. Use "Activities" to log all customer interactions
2. Record calls, emails, meetings, and notes
3. Link activities to specific contacts, leads, or deals
4. Track interaction history for better customer service

## Customization

### Adding New Fields
Edit the models in `crm_app/models.py` and run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

### Modifying UI
- Templates are in `templates/crm_app/`
- Static files can be added to `static/` directory
- Bootstrap classes can be customized in `templates/base.html`

## Production Deployment

### Database Configuration
For production, update `settings.py` to use PostgreSQL:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'crm_db',
        'USER': 'your_db_user',
        'PASSWORD': 'your_db_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### Security Settings
- Change `SECRET_KEY` in production
- Set `DEBUG = False`
- Configure `ALLOWED_HOSTS`
- Use environment variables for sensitive data

## Support

For technical support or feature requests, contact your system administrator.

## License

Internal use only - Proprietary software for [Your Company Name]
