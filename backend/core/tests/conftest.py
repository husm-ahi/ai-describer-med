"""
Pytest configuration and fixtures for core application tests.
"""
import pytest
from django.contrib.auth import get_user_model
from backend.core.models import SystemPrompt, LLMLog, AuditLog

User = get_user_model()


@pytest.fixture
def user(db):
    """Create a regular test user."""
    return User.objects.create_user(
        username='testuser',
        password='testpass123'
    )


@pytest.fixture
def admin_user(db):
    """Create an admin test user."""
    return User.objects.create_superuser(
        username='admin',
        password='adminpass123'
    )


@pytest.fixture
def staff_user(db):
    """Create a staff test user."""
    user = User.objects.create_user(
        username='staffuser',
        password='staffpass123'
    )
    user.is_staff = True
    user.save()
    return user


@pytest.fixture
def system_prompt(db, admin_user):
    """Create a test system prompt."""
    return SystemPrompt.objects.create(
        version='1.0',
        content='Test prompt with {{{USER_INPUT}}} placeholder',
        is_active=True,
        created_by=admin_user
    )


@pytest.fixture
def inactive_system_prompt(db, admin_user):
    """Create an inactive test system prompt."""
    return SystemPrompt.objects.create(
        version='0.9',
        content='Old inactive prompt',
        is_active=False,
        created_by=admin_user
    )


@pytest.fixture
def llm_log(db, user):
    """Create a test LLM log."""
    return LLMLog.create_log(
        user=user,
        user_prompt='Test prompt',
        llm_response='Test response',
        model_name='test-model',
        prompt_version='1.0',
        processing_time_ms=100
    )


@pytest.fixture
def audit_log(db, admin_user, user):
    """Create a test audit log."""
    return AuditLog.log_action(
        action='user_created',
        admin=admin_user,
        target_user=user,
        test=True
    )
