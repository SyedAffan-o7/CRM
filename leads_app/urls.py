from django.urls import path
from . import views as crm_views
from customers_app import views as customers_views
from accounts_app import views as accounts_views
from deals_app import views as deals_views
from activities_app import views as activities_views

app_name = 'leads_app'

urlpatterns = [
    # Lead management URLs
    path('update-stage/<int:pk>/', crm_views.lead_update_stage, name='lead_update_stage'),
    path('update-status/<int:pk>/', crm_views.lead_update_status, name='lead_update_status'),
    path('update-reason/<int:pk>/', crm_views.lead_update_reason, name='lead_update_reason'),
    path('update-assignment/<int:pk>/', crm_views.lead_update_assignment, name='lead_update_assignment'),

    # Follow-up management URLs are now handled by crm_app
]
