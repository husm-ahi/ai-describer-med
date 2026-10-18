"""
Tests for core.views module.
"""
import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from backend.core.models import SystemPrompt, LLMLog, AuditLog
from backend.core.views import generate_random_password
import json

User = get_user_model()


@pytest.fixture
def client():
    """Create a test client."""
    return Client()


@pytest.mark.unit
class TestGenerateRandomPassword:
    """Tests for generate_random_password function."""
    
    def test_password_length(self):
        """Test that generated password has correct length."""
        password = generate_random_password()
        # Default length should be 12 or more
        assert len(password) >= 12
    
    def test_password_uniqueness(self):
        """Test that each generated password is unique."""
        passwords = [generate_random_password() for _ in range(10)]
        assert len(set(passwords)) == 10


@pytest.mark.django_db
class TestSetupView:
    """Tests for setup view."""
    
    def test_setup_redirects_if_admin_exists(self, client, admin_user):
        """Test that setup redirects if admin already exists."""
        response = client.get('/setup/')
        assert response.status_code == 302
        assert '/admin-dashboard/' in response.url
    
    def test_setup_displays_form_if_no_admin(self, client):
        """Test that setup displays form when no admin exists."""
        # Make sure no superuser exists
        User.objects.filter(is_superuser=True).delete()
        
        response = client.get('/setup/')
        assert response.status_code == 200
        assert 'core/setup.html' in [t.name for t in response.templates]
    
    def test_setup_creates_admin(self, client, db):
        """Test creating first admin through setup."""
        # Make sure no users exist
        User.objects.all().delete()
        
        response = client.post('/setup/', {
            'username': 'newadmin',
            'password': 'testpass123',
            'password_confirm': 'testpass123'
        })
        
        # Should redirect to admin dashboard
        assert response.status_code == 302
        
        # Check user was created
        user = User.objects.get(username='newadmin')
        assert user.is_superuser is True
        assert user.is_staff is True
    
    def test_setup_password_mismatch(self, client, db):
        """Test setup with mismatched passwords."""
        User.objects.all().delete()
        
        response = client.post('/setup/', {
            'username': 'newadmin',
            'password': 'testpass123',
            'password_confirm': 'different'
        })
        
        assert response.status_code == 200
        assert 'パスワードが一致しません' in response.content.decode()
    
    def test_setup_short_password(self, client, db):
        """Test setup with password too short."""
        User.objects.all().delete()
        
        response = client.post('/setup/', {
            'username': 'newadmin',
            'password': 'short',
            'password_confirm': 'short'
        })
        
        assert response.status_code == 200
        assert '8文字以上' in response.content.decode()


@pytest.mark.django_db
class TestIndexView:
    """Tests for index view."""
    
    def test_index_requires_authentication(self, client):
        """Test that index requires authentication."""
        response = client.get('/')
        assert response.status_code == 302
        assert '/accounts/login/' in response.url
    
    def test_index_displays_for_authenticated_user(self, client, user):
        """Test that authenticated user can access index."""
        client.force_login(user)
        response = client.get('/')
        assert response.status_code == 200
        assert 'core/index.html' in [t.name for t in response.templates]


@pytest.mark.django_db
class TestAdminDashboard:
    """Tests for admin dashboard views."""
    
    def test_admin_dashboard_requires_staff(self, client, user):
        """Test that admin dashboard requires staff permission."""
        client.force_login(user)
        response = client.get('/admin-dashboard/')
        assert response.status_code == 302
        assert '/accounts/login/' in response.url
    
    def test_admin_dashboard_accessible_by_staff(self, client, staff_user):
        """Test that staff user can access admin dashboard."""
        client.force_login(staff_user)
        response = client.get('/admin-dashboard/')
        assert response.status_code == 200
        assert 'core/admin_dashboard.html' in [t.name for t in response.templates]
    
    def test_admin_dashboard_displays_statistics(self, client, staff_user, system_prompt, llm_log):
        """Test that admin dashboard displays correct statistics."""
        client.force_login(staff_user)
        response = client.get('/admin-dashboard/')
        
        assert response.status_code == 200
        context = response.context
        assert context['active_prompt'] == system_prompt
        assert context['total_logs'] >= 1
        assert context['total_users'] >= 1


@pytest.mark.django_db
class TestGeneratePasswordAPI:
    """Tests for generate password API."""
    
    def test_generate_password_api_requires_staff(self, client, user):
        """Test that API requires staff permission."""
        client.force_login(user)
        response = client.get('/admin-dashboard/generate-password/')
        assert response.status_code == 302
    
    def test_generate_password_api_returns_password(self, client, staff_user):
        """Test that API returns a password."""
        client.force_login(staff_user)
        response = client.get('/admin-dashboard/generate-password/')
        
        assert response.status_code == 200
        data = json.loads(response.content)
        assert 'password' in data
        assert len(data['password']) >= 12


@pytest.mark.django_db
class TestManagePrompts:
    """Tests for prompt management views."""
    
    def test_manage_prompts_requires_staff(self, client, user):
        """Test that prompt management requires staff permission."""
        client.force_login(user)
        response = client.get('/admin-dashboard/prompts/')
        assert response.status_code == 302
    
    def test_manage_prompts_displays_prompts(self, client, staff_user, system_prompt):
        """Test that prompt management page displays prompts."""
        client.force_login(staff_user)
        response = client.get('/admin-dashboard/prompts/')
        
        assert response.status_code == 200
        assert 'core/manage_prompts.html' in [t.name for t in response.templates]
        assert system_prompt in response.context['prompts']
    
    def test_create_prompt(self, client, staff_user):
        """Test creating a new prompt."""
        client.force_login(staff_user)
        
        response = client.post('/admin-dashboard/prompts/', {
            'action': 'create',
            'version': '2.0',
            'content': 'New test prompt'
        })
        
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        
        # Check prompt was created
        prompt = SystemPrompt.objects.get(version='2.0')
        assert prompt.content == 'New test prompt'
        assert prompt.is_active is False
    
    def test_activate_prompt(self, client, staff_user, system_prompt, inactive_system_prompt):
        """Test activating a prompt."""
        client.force_login(staff_user)
        
        response = client.post('/admin-dashboard/prompts/', {
            'action': 'activate',
            'prompt_id': inactive_system_prompt.id
        })
        
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        
        # Check activation
        system_prompt.refresh_from_db()
        inactive_system_prompt.refresh_from_db()
        
        assert system_prompt.is_active is False
        assert inactive_system_prompt.is_active is True
    
    def test_cannot_delete_active_prompt(self, client, staff_user, system_prompt):
        """Test that active prompt cannot be deleted."""
        client.force_login(staff_user)
        
        response = client.post('/admin-dashboard/prompts/', {
            'action': 'delete',
            'prompt_id': system_prompt.id
        })
        
        assert response.status_code == 400
        data = json.loads(response.content)
        assert 'error' in data


@pytest.mark.django_db
class TestViewLogs:
    """Tests for log viewing."""
    
    def test_view_logs_requires_staff(self, client, user):
        """Test that log viewing requires staff permission."""
        client.force_login(user)
        response = client.get('/admin-dashboard/logs/')
        assert response.status_code == 302
    
    def test_view_logs_displays_logs(self, client, staff_user, llm_log):
        """Test that log viewing page displays logs."""
        client.force_login(staff_user)
        response = client.get('/admin-dashboard/logs/')
        
        assert response.status_code == 200
        assert 'core/view_logs.html' in [t.name for t in response.templates]
        assert llm_log in response.context['page_obj']
    
    def test_view_logs_search(self, client, staff_user, user):
        """Test log search functionality."""
        client.force_login(staff_user)
        
        # Create logs with different prompts
        LLMLog.create_log(user=user, user_prompt='test search', llm_response='response1')
        LLMLog.create_log(user=user, user_prompt='other prompt', llm_response='response2')
        
        response = client.get('/admin-dashboard/logs/?q=search')
        
        assert response.status_code == 200
        logs = list(response.context['page_obj'])
        assert any('test search' in log.user_prompt for log in logs)


@pytest.mark.django_db
class TestManageUsers:
    """Tests for user management."""
    
    def test_manage_users_requires_staff(self, client, user):
        """Test that user management requires staff permission."""
        client.force_login(user)
        response = client.get('/admin-dashboard/users/')
        assert response.status_code == 302
    
    def test_manage_users_displays_users(self, client, staff_user, user):
        """Test that user management page displays users."""
        client.force_login(staff_user)
        response = client.get('/admin-dashboard/users/')
        
        assert response.status_code == 200
        assert 'core/manage_users.html' in [t.name for t in response.templates]
        assert user in response.context['users']
    
    def test_create_user(self, client, staff_user):
        """Test creating a new user."""
        client.force_login(staff_user)
        
        response = client.post('/admin-dashboard/users/', {
            'action': 'create',
            'username': 'newuser',
            'role': 'user'
        })
        
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert 'password' in data
        
        # Check user was created
        user = User.objects.get(username='newuser')
        assert user.is_active is True
        assert user.is_staff is False
    
    def test_create_staff_user(self, client, staff_user):
        """Test creating a staff user."""
        client.force_login(staff_user)
        
        response = client.post('/admin-dashboard/users/', {
            'action': 'create',
            'username': 'newstaff',
            'role': 'staff'
        })
        
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        
        # Check user was created as staff
        user = User.objects.get(username='newstaff')
        assert user.is_staff is True
        assert user.is_superuser is False
    
    def test_disable_user(self, client, staff_user, user):
        """Test disabling a user."""
        client.force_login(staff_user)
        
        response = client.post('/admin-dashboard/users/', {
            'action': 'disable',
            'user_id': user.id
        })
        
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        
        # Check user was disabled
        user.refresh_from_db()
        assert user.is_active is False
    
    def test_cannot_disable_superuser(self, client, staff_user, admin_user):
        """Test that superuser cannot be disabled."""
        client.force_login(staff_user)
        
        response = client.post('/admin-dashboard/users/', {
            'action': 'disable',
            'user_id': admin_user.id
        })
        
        assert response.status_code == 400
        data = json.loads(response.content)
        assert 'error' in data
    
    def test_promote_to_staff(self, client, staff_user, user):
        """Test promoting user to staff."""
        client.force_login(staff_user)
        
        response = client.post('/admin-dashboard/users/', {
            'action': 'promote_to_staff',
            'user_id': user.id
        })
        
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        
        # Check user was promoted
        user.refresh_from_db()
        assert user.is_staff is True
        assert user.is_superuser is False


@pytest.mark.django_db
class TestSecurityRegressions:
    """Regression tests for security review findings."""

    def test_setup_closed_when_only_non_superusers_exist(self, client, staff_user):
        """Setup must not reopen just because no superuser remains."""
        response = client.post('/setup/', {
            'username': 'attacker',
            'password': 'attackerpass123',
            'password_confirm': 'attackerpass123'
        })

        assert response.status_code == 302
        assert not User.objects.filter(username='attacker').exists()

    def test_setup_rejects_missing_username(self, client, db):
        response = client.post('/setup/', {
            'password': 'testpass123',
            'password_confirm': 'testpass123'
        })

        assert response.status_code == 200
        assert User.objects.count() == 0

    def test_promote_to_staff_cannot_strip_superuser(self, client, staff_user, admin_user):
        client.force_login(staff_user)

        response = client.post('/admin-dashboard/users/', {
            'action': 'promote_to_staff',
            'user_id': admin_user.id
        })

        assert response.status_code == 400
        admin_user.refresh_from_db()
        assert admin_user.is_superuser is True

    def test_reset_password_rejects_empty_password(self, client, staff_user, user):
        client.force_login(staff_user)

        response = client.post('/admin-dashboard/users/', {
            'action': 'reset_password',
            'user_id': user.id,
        })

        assert response.status_code == 400
        user.refresh_from_db()
        assert user.check_password('testpass123')

    def test_reset_password_rejects_weak_password(self, client, staff_user, user):
        client.force_login(staff_user)

        response = client.post('/admin-dashboard/users/', {
            'action': 'reset_password',
            'user_id': user.id,
            'password': '12345678',
        })

        assert response.status_code == 400
        user.refresh_from_db()
        assert user.check_password('testpass123')

    def test_reset_password_accepts_generated_password(self, client, staff_user, user):
        client.force_login(staff_user)
        password = generate_random_password()

        response = client.post('/admin-dashboard/users/', {
            'action': 'reset_password',
            'user_id': user.id,
            'password': password,
        })

        assert response.status_code == 200
        user.refresh_from_db()
        assert user.check_password(password)

    def test_prompt_fields_not_rendered_into_inline_js(self, client, staff_user):
        """Prompt version/content must not be able to break out into inline JavaScript."""
        SystemPrompt.objects.create(
            version="x');alert(1);//",
            content='${alert(2)}`',
            created_by=staff_user,
        )
        client.force_login(staff_user)

        response = client.get('/admin-dashboard/prompts/')
        html = response.content.decode()

        assert "editPrompt(this)" in html
        assert "alert(1)" not in html.split('editPrompt(')[1].split(')')[0]
        assert 'data-version="x&#x27;);alert(1);//"' in html


@pytest.mark.django_db
class TestStaffAccountProtection:
    """Only superusers may manage other staff accounts."""

    @pytest.fixture
    def other_staff(self, db):
        return User.objects.create_user(
            username='otherstaff',
            password='otherstaffpass123',
            is_staff=True,
        )

    @pytest.mark.parametrize('action, extra', [
        ('disable', {}),
        ('enable', {}),
        ('reset_password', {'password': 'Xk7pQ2mZr9Lw'}),
        ('demote_to_user', {}),
    ])
    def test_staff_cannot_manage_other_staff(self, client, staff_user, other_staff, action, extra):
        client.force_login(staff_user)

        response = client.post('/admin-dashboard/users/', {
            'action': action,
            'user_id': other_staff.id,
            **extra,
        })

        assert response.status_code == 403
        other_staff.refresh_from_db()
        assert other_staff.is_staff is True
        assert other_staff.is_active is True
        assert other_staff.check_password('otherstaffpass123')

    @pytest.mark.parametrize('action, extra', [
        ('disable', {}),
        ('reset_password', {'password': 'Xk7pQ2mZr9Lw'}),
        ('demote_to_user', {}),
    ])
    def test_superuser_can_manage_staff(self, client, admin_user, other_staff, action, extra):
        client.force_login(admin_user)

        response = client.post('/admin-dashboard/users/', {
            'action': action,
            'user_id': other_staff.id,
            **extra,
        })

        assert response.status_code == 200

    def test_staff_can_reset_own_password(self, client, staff_user):
        client.force_login(staff_user)

        response = client.post('/admin-dashboard/users/', {
            'action': 'reset_password',
            'user_id': staff_user.id,
            'password': 'Xk7pQ2mZr9Lw',
        })

        assert response.status_code == 200

    def test_staff_can_still_manage_regular_users(self, client, staff_user, user):
        client.force_login(staff_user)

        response = client.post('/admin-dashboard/users/', {
            'action': 'disable',
            'user_id': user.id,
        })

        assert response.status_code == 200

    def test_staff_rows_hide_actions_for_non_superuser(self, client, staff_user, other_staff, user):
        client.force_login(staff_user)

        html = client.get('/admin-dashboard/users/').content.decode()

        assert f"disableUser({other_staff.id}," not in html
        assert f"disableUser({user.id}," in html
