"""
URL configuration for core application.
"""
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.index, name='index'),
    path('setup/', views.setup, name='setup'),
    # Note: LLM processing is handled via WebSocket at /ws/llm/ (see routing.py)
    
    # Admin Dashboard URLs
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/prompts/', views.manage_prompts, name='manage_prompts'),
    path('admin-dashboard/prompts/load-default/', views.load_default_prompt, name='load_default_prompt'),
    path('admin-dashboard/logs/', views.view_logs, name='view_logs'),
    path('admin-dashboard/users/', views.manage_users, name='manage_users'),
    path('admin-dashboard/generate-password/', views.generate_password_api, name='generate_password'),
]
