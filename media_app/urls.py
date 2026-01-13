from django.urls import path
from . import views

app_name = 'media_app'

urlpatterns = [
    path('', views.media_gallery, name='media_gallery'),
]
