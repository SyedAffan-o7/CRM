from django.urls import path
from . import views

app_name = 'notifications_app'

urlpatterns = [
    # User notification views
    path('', views.notification_list, name='notification_list'),
    path('<int:notification_id>/', views.notification_detail, name='notification_detail'),
    path('<int:notification_id>/read/', views.mark_as_read, name='mark_as_read'),
    path('mark-all-read/', views.mark_all_as_read, name='mark_all_as_read'),
    path('<int:notification_id>/delete/', views.delete_notification, name='delete_notification'),
    path('preferences/', views.notification_preferences, name='notification_preferences'),
    
    # AJAX endpoints
    path('api/unread/', views.get_unread_notifications, name='get_unread_notifications'),
    
    # Admin views
    path('admin/dashboard/', views.admin_notification_dashboard, name='admin_dashboard'),
    path('admin/test/', views.send_test_notification, name='send_test_notification'),
]
