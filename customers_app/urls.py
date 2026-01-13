from django.urls import path
from . import views

app_name = 'customers_app'

urlpatterns = [
    # Customers (Contacts)
    path('customers/', views.contact_list, name='customer_list'),
    path('customers/add/', views.contact_add, name='customer_add'),
    # Static routes must come before dynamic <str:pk> to prevent conflicts
    path('customers/import/', views.customer_import, name='customer_import'),
    path('customers/sample-csv/', views.download_sample_csv, name='download_sample'),
    # More specific routes before the generic detail route
    path('customers/<str:pk>/edit/', views.contact_edit, name='customer_edit'),
    path('customers/<str:pk>/', views.contact_detail, name='customer_detail'),
    path('customers/<str:pk>/log-activity/', views.log_activity_for_contact, name='log_activity_for_contact'),
]
