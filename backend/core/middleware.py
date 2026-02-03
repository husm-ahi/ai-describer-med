"""
Custom middleware for core application.
"""
from django.shortcuts import redirect
from django.contrib.auth import get_user_model
from django.urls import resolve

User = get_user_model()


class SetupRedirectMiddleware:
    """
    Middleware to redirect to setup page when accessing login page
    if no users exist in the database.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if accessing login page
        if request.path.startswith('/accounts/login'):
            # Check if any user exists
            if User.objects.count() == 0:
                # Redirect to setup page if no users exist
                return redirect('/setup/')
        
        response = self.get_response(request)
        return response
