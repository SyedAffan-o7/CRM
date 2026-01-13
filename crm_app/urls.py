from django.urls import path

from . import views
from customers_app import views as customer_views
from activities_app import views as activity_views
from leads_app import views as lead_views

app_name = 'crm_app'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Reports (Super Admin only)
    path('reports/enquiries/', views.report_enquiries_pipeline, name='report_enquiries_pipeline'),
    path('reports/followups/', views.report_followups_compliance, name='report_followups_compliance'),

    # Enquiries
    path('enquiries/', lead_views.lead_list, name='lead_list'),
    path('enquiries/add/', lead_views.lead_add, name='lead_add'),
    path('enquiries/bulk-import/', lead_views.lead_bulk_import, name='lead_bulk_import'),
    path('enquiries/bulk-export/', lead_views.lead_bulk_export, name='lead_bulk_export'),
    path('enquiries/bulk-delete/', lead_views.lead_bulk_delete, name='lead_bulk_delete'),
    # WhatsApp upload endpoint must come before the generic <str:pk> pattern
    path('enquiries/upload-whatsapp-file/', lead_views.upload_whatsapp_file, name='upload_whatsapp_file'),
    path('enquiries/<str:pk>/', lead_views.lead_detail, name='lead_detail'),
    path('enquiries/<str:pk>/edit/', lead_views.lead_edit, name='lead_edit'),
    path('enquiries/<str:pk>/quick-add/', lead_views.lead_quick_add, name='lead_quick_add'),
    path('enquiries/<str:pk>/convert/', lead_views.lead_convert, name='lead_convert'),
    path('enquiries/<str:pk>/accept/', lead_views.lead_accept, name='lead_accept'),
    path('enquiries/<str:pk>/reject/', lead_views.lead_reject, name='lead_reject'),
    path('enquiries/<str:pk>/assignment/accept/', lead_views.assignment_accept, name='assignment_accept'),
    path('enquiries/<str:pk>/assignment/reject/', lead_views.assignment_reject, name='assignment_reject'),
    path('enquiries/<str:pk>/update-status/', lead_views.lead_update_status, name='lead_update_status'),
    path('enquiries/<str:pk>/update-stage/', lead_views.lead_update_stage, name='lead_update_stage'),
    path('enquiries/<str:pk>/update-assignment/', lead_views.lead_update_assignment, name='lead_update_assignment'),
    path('enquiries/<str:pk>/delete/', lead_views.lead_delete, name='lead_delete'),
    path('enquiries/<str:pk>/update-reason/', lead_views.lead_update_reason, name='lead_update_reason'),

    # Enquiry Stages
    path('enquiry-stages/', views.enquiry_stages, name='enquiry_stages'),

    # Contacts (use customers_app views)
    path('contacts/', customer_views.contact_list, name='contact_list'),
    path('contacts/add/', customer_views.contact_add, name='contact_add'),
    path('contacts/<str:pk>/', customer_views.contact_detail, name='contact_detail'),
    path('contacts/<str:pk>/edit/', customer_views.contact_edit, name='contact_edit'),

    # Accounts
    path('accounts/', views.account_list, name='account_list'),
    path('accounts/add/', views.account_add, name='account_add'),
    path('accounts/<str:pk>/', views.account_detail, name='account_detail'),
    path('accounts/<str:pk>/edit/', views.account_edit, name='account_edit'),

    # Deals
    path('deals/', views.deal_list, name='deal_list'),
    path('deals/add/', views.deal_add, name='deal_add'),
    path('deals/<int:pk>/', views.deal_detail, name='deal_detail'),
    path('deals/<int:pk>/edit/', views.deal_edit, name='deal_edit'),

    # Activities (use activities_app views)
    path('activities/', activity_views.activity_list, name='activity_list'),
    path('activities/add/', activity_views.activity_add, name='activity_add'),


    # Settings URLs (Super Admin only)
    path('settings/', views.settings, name='settings'),
    path('settings/lead-sources/', views.lead_source_list, name='lead_source_list'),
    path('settings/lead-sources/add/', views.lead_source_add, name='lead_source_add'),
    path('settings/lead-sources/<int:pk>/edit/', views.lead_source_edit, name='lead_source_edit'),
    path('settings/lead-sources/<int:pk>/delete/', views.lead_source_delete, name='lead_source_delete'),
    path('settings/reasons/', views.reason_list, name='reason_list'),
    path('settings/reasons/add/', views.reason_add, name='reason_add'),
    path('settings/reasons/<int:pk>/edit/', views.reason_edit, name='reason_edit'),
    path('settings/reasons/<int:pk>/delete/', views.reason_delete, name='reason_delete'),

    # Follow-up URLs
    path('followup/create/<int:lead_id>/', lead_views.followup_create, name='followup_create'),
    path('followup/<int:followup_id>/update-status/', lead_views.followup_update_status, name='followup_update_status'),
    path('followup/<int:followup_id>/edit/', lead_views.followup_edit, name='followup_edit'),
    path('api/followups/', lead_views.get_followups, name='get_followups'),
    # API endpoints
    path('get_subcategories/<int:category_id>/', views.get_subcategories, name='get_subcategories'),
    path('enquiries/<str:lead_id>/products/', views.lead_products_api, name='lead_products_api'),
]
