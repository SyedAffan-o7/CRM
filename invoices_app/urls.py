from django.urls import path

from . import views

app_name = 'invoices_app'

urlpatterns = [
    path('', views.invoice_list, name='invoice_list'),
    path('add/', views.invoice_create, name='invoice_add'),
    path('<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('<int:pk>/edit/', views.invoice_edit, name='invoice_edit'),
    path('api/contact/<int:contact_id>/leads/', views.contact_leads_api, name='contact_leads_api'),
    path('api/lead/<int:lead_id>/items/', views.lead_items_api, name='lead_items_api'),
]
