from django.urls import path
from . import views

app_name = 'outbound_app'

urlpatterns = [
    # When included at project path('outbound/', include('outbound_app.urls')),
    # this will resolve to /outbound/
    path('', views.campaign_list, name='outbound_list'),
    path('dashboard/', views.outbound_dashboard, name='outbound_dashboard'),
    path('add/', views.outbound_add, name='outbound_add'),
    path('customer/<str:contact_id>/', views.customer_outbound, name='customer_outbound'),
    path('customer/<str:contact_id>/drawer/', views.customer_outbound_drawer, name='customer_outbound_drawer'),
    path('customer/<str:contact_id>/send-catalog/', views.send_catalog, name='send_catalog'),
    path('activity/log/<str:pk>/', views.log_activity, name='log_activity'),
    path('<int:pk>/', views.outbound_detail, name='outbound_detail'),
    path('<int:pk>/edit/', views.outbound_edit, name='outbound_edit'),
    path('<int:pk>/convert-to-enquiry/', views.outbound_convert_to_enquiry, name='outbound_convert_to_enquiry'),
    path('<int:pk>/delete/', views.outbound_delete, name='outbound_delete'),

    # APIs
    path('api/outbound/', views.outbound_list_api, name='outbound-list-api'),
    path('api/outbound/<int:pk>/', views.outbound_detail_api, name='outbound-detail-api'),

    # Export
    path('export/csv/', views.outbound_export_csv, name='outbound-export-csv'),
]
