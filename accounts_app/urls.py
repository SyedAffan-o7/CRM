from django.urls import path
from . import views

app_name = 'accounts_app'

urlpatterns = [
    # User Management (Superuser only)
    path('users/', views.user_management_dashboard, name='user_management'),
    path('users/create/', views.create_user, name='create_user'),
    path('users/<int:user_id>/edit/', views.edit_user, name='edit_user'),
    path('users/<int:user_id>/toggle/', views.toggle_user_status, name='toggle_user_status'),
    path('users/<int:user_id>/permissions/', views.user_permissions_detail, name='user_permissions_detail'),
    path('users/<int:user_id>/delete/', views.delete_user, name='delete_user'),
    path('users/<int:user_id>/reset-password/', views.reset_user_password, name='reset_user_password'),
    path('users/<int:user_id>/credentials/', views.view_user_credentials, name='view_user_credentials'),
    path('users/bulk-actions/', views.bulk_user_actions, name='bulk_user_actions'),

    # Role Management (Superuser only)
    path('roles/', views.role_management, name='role_management'),
    path('roles/<int:role_id>/delete/', views.delete_role, name='delete_role'),
]
