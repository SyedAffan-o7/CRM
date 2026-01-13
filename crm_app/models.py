from accounts_app.models import Account
from customers_app.models import Contact
from leads_app.models import Reason, Product, LeadSource, Lead, LeadProduct
from deals_app.models import Deal
from activities_app.models import ActivityLog

__all__ = [
    'Account',
    'Contact',
    'Reason',
    'Product',
    'LeadSource',
    'Lead',
    'LeadProduct',
    'Deal',
    'ActivityLog',
]
