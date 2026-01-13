from django.urls import path
from . import views

app_name = 'deals_app'

urlpatterns = [
    path('deals/', views.deal_list, name='deal_list'),
    path('deals/add/', views.deal_add, name='deal_add'),
    path('deals/<int:pk>/', views.deal_detail, name='deal_detail'),
    path('deals/<int:pk>/edit/', views.deal_edit, name='deal_edit'),
]
