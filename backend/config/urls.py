"""
URL configuration for AI Describer Medical project.
"""
from django.http import JsonResponse
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

# Blocked pages view
blocked_page = TemplateView.as_view(template_name='account/signup_closed.html')

urlpatterns = [
    # Health check endpoint for Docker/load balancer
    path('health/', lambda request: JsonResponse({'status': 'ok'})),

    # path('admin/', admin.site.urls),  # Not using Django Admin

    # Block user self-registration and password reset
    re_path(r'^accounts/signup/', blocked_page, name='account_signup_blocked'),
    re_path(r'^accounts/password/reset/', blocked_page, name='account_reset_password_blocked'),

    # Allow allauth URLs (login, logout, etc.)
    path('accounts/', include('allauth.urls')),

    path('', include('backend.core.urls')),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
