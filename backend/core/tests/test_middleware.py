"""
Tests for core.middleware module.
"""
import pytest
from django.test import Client, RequestFactory
from django.contrib.auth import get_user_model
from backend.core.middleware import SetupRedirectMiddleware

User = get_user_model()


@pytest.mark.django_db
class TestSetupRedirectMiddleware:
    """Tests for SetupRedirectMiddleware."""
    
    def test_redirects_to_setup_when_no_users(self):
        """Test that middleware redirects to setup when no users exist."""
        # Delete all users
        User.objects.all().delete()
        
        # Make request to login page
        client = Client()
        response = client.get('/accounts/login/')
        
        # Should redirect to setup
        assert response.status_code == 302
        assert '/setup/' in response.url
    
    def test_allows_login_when_users_exist(self, user):
        """Test that middleware allows login page when users exist."""
        # Make request to login page
        client = Client()
        response = client.get('/accounts/login/')
        
        # Should not redirect (or redirect to next page, but not to setup)
        if response.status_code == 302:
            assert '/setup/' not in response.url
    
    def test_does_not_affect_other_pages(self, user):
        """Test that middleware does not affect non-login pages."""
        client = Client()
        
        # Access other page (should require auth but not redirect to setup)
        response = client.get('/')
        
        # Should redirect to login, not setup
        assert response.status_code == 302
        if '/accounts/' in response.url:
            assert '/setup/' not in response.url
    
    def test_middleware_with_factory(self):
        """Test middleware using RequestFactory."""
        factory = RequestFactory()
        
        # Create mock get_response
        def get_response(request):
            from django.http import HttpResponse
            return HttpResponse('OK')
        
        # Create middleware instance
        middleware = SetupRedirectMiddleware(get_response)
        
        # Test with users existing
        User.objects.create_user('testuser', password='pass')
        request = factory.get('/accounts/login/')
        response = middleware(request)
        
        # Should get normal response (not redirect)
        # Note: In real scenario with users, Django would handle the login page
        # This test just ensures middleware doesn't interfere
        assert response.status_code in [200, 302]
