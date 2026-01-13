from django.urls import path
from . import views

app_name = 'activities_app'

urlpatterns = [
    # Activities
    path('activities/', views.activity_list, name='activity_list'),
    path('activities/add/', views.activity_add, name='activity_add'),
]
