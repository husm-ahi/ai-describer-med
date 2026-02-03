"""
Custom adapters for django-allauth.
"""
from allauth.account.adapter import DefaultAccountAdapter
from django.http import HttpResponseForbidden


class NoSignupAccountAdapter(DefaultAccountAdapter):
    """
    Adapter that disables user self-registration and password reset.
    Only administrators can create/manage users.
    """
    
    def is_open_for_signup(self, request):
        """
        Disable user self-registration.
        Users can only be created by administrators.
        """
        return False
    
    def send_mail(self, template_prefix, email, context):
        """
        Disable all email sending (password reset, email verification, etc.).
        Password resets must be done by administrators.
        """
        # Do not send any emails
        pass
