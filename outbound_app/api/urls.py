from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ContactViewSet, 
    OutboundActivityViewSet, 
    MessageTemplateViewSet,
    CampaignViewSet,
    OutboundAnalyticsOverview,
    get_contact_communication_links
)

router = DefaultRouter()
router.register(r'contacts', ContactViewSet, basename='api-contacts')
router.register(r'activities', OutboundActivityViewSet, basename='api-activities')
router.register(r'templates', MessageTemplateViewSet, basename='api-templates')
router.register(r'campaigns', CampaignViewSet, basename='api-campaigns')

urlpatterns = [
    path('', include(router.urls)),
    path('analytics/overview/', OutboundAnalyticsOverview.as_view(), name='api-analytics-overview'),
    path('contacts/<int:contact_id>/communication-links/', get_contact_communication_links, name='api-communication-links'),
]
