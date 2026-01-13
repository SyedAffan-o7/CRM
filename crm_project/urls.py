"""crm_project URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from crm_app.views import healthz, analytics_overview
from django.views.static import serve

from django.http import HttpResponse

def favicon_view(request):
    # Return empty response to avoid 404 errors
    return HttpResponse(b'', content_type='image/x-icon')

urlpatterns = [
    # Custom admin redirects for legacy URLs - must come BEFORE admin.site.urls
    re_path(r'^admin/crm_app/product/(?P<path>.*)$', RedirectView.as_view(url='/admin/leads_app/product/%(path)s', permanent=True)),
    re_path(r'^admin/crm_app/product/$', RedirectView.as_view(url='/admin/leads_app/product/', permanent=True)),

    path('admin/', admin.site.urls),
    path('favicon.ico', favicon_view),

    # Legacy app URLs (proxying crm_app views)
    path('', include('crm_app.urls')),

    # Domain-specific apps
    path('', include('customers_app.urls')),
    path('', include('deals_app.urls')),
    path('', include('leads_app.urls')),
    # Products settings (namespaced include for stable URL reversing)
    path(
        "settings/products/",
        include(("products.urls", "products"), namespace="products"),
    ),

    # User and Role Management (moved to settings)
    path('settings/', include('accounts_app.urls')),

    # Outbound app
    path('outbound/', include('outbound_app.urls')),

    # Invoices app
    path(
        'invoices/',
        include(('invoices_app.urls', 'invoices_app'), namespace='invoices_app'),
    ),

    # Notifications
    path('notifications/', include('notifications_app.urls')),

    # Media Gallery
    path('media/', include('media_app.urls')),

    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('healthz/', healthz, name='healthz'),

    # Analytics API (dashboard - enquiries + outbound charts)
    # NOTE: This must come BEFORE the generic 'api/' include so that
    # /api/analytics/overview/ is handled by crm_app.views.analytics_overview
    # and not by outbound_app.api.OutboundAnalyticsOverview.
    path('api/analytics/overview/', analytics_overview, name='api-analytics-overview'),

    # Outbound API (contacts, activities, outbound analytics, etc.)
    path('api/', include('outbound_app.api.urls')),
]

# Serve media files during development AND production (for small deployments)
# Use a safe fallback for MEDIA_ROOT when S3 is enabled (MEDIA_ROOT may be empty)
_media_root = settings.MEDIA_ROOT or (settings.BASE_DIR / 'media')
urlpatterns += static(settings.MEDIA_URL, document_root=_media_root)
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': _media_root}),
]
