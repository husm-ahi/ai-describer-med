"""
Tests for core.models module.
"""
import pytest
from django.contrib.auth import get_user_model
from django.conf import settings
from backend.core.models import SystemPrompt, LLMLog, AuditLog, hash_user_id

User = get_user_model()


@pytest.mark.unit
class TestHashUserId:
    """Tests for hash_user_id function."""
    
    def test_hash_user_id_returns_16_chars(self):
        """Test that hash_user_id returns exactly 16 characters."""
        result = hash_user_id('testuser')
        assert len(result) == 16
    
    def test_hash_user_id_consistent(self):
        """Test that hash_user_id returns same result for same input."""
        username = 'testuser'
        result1 = hash_user_id(username)
        result2 = hash_user_id(username)
        assert result1 == result2
    
    def test_hash_user_id_different_for_different_users(self):
        """Test that different usernames produce different hashes."""
        result1 = hash_user_id('user1')
        result2 = hash_user_id('user2')
        assert result1 != result2


@pytest.mark.unit
@pytest.mark.django_db
class TestSystemPrompt:
    """Tests for SystemPrompt model."""
    
    def test_create_system_prompt(self, admin_user):
        """Test creating a system prompt."""
        prompt = SystemPrompt.objects.create(
            version='1.0',
            content='Test prompt',
            is_active=True,
            created_by=admin_user
        )
        assert prompt.version == '1.0'
        assert prompt.content == 'Test prompt'
        assert prompt.is_active is True
        assert prompt.created_by == admin_user
    
    def test_only_one_active_prompt(self, admin_user):
        """Test that only one prompt can be active at a time."""
        # Create first active prompt
        prompt1 = SystemPrompt.objects.create(
            version='1.0',
            content='First prompt',
            is_active=True,
            created_by=admin_user
        )
        
        # Create second active prompt
        prompt2 = SystemPrompt.objects.create(
            version='2.0',
            content='Second prompt',
            is_active=True,
            created_by=admin_user
        )
        
        # Refresh first prompt from database
        prompt1.refresh_from_db()
        
        # First prompt should now be inactive
        assert prompt1.is_active is False
        assert prompt2.is_active is True
    
    def test_str_representation(self, system_prompt):
        """Test string representation of system prompt."""
        assert 'v1.0' in str(system_prompt)
        assert 'Active' in str(system_prompt)
    
    def test_inactive_prompt_str(self, inactive_system_prompt):
        """Test string representation of inactive prompt."""
        assert 'v0.9' in str(inactive_system_prompt)
        assert 'Active' not in str(inactive_system_prompt)
    
    def test_ordering(self, admin_user):
        """Test that prompts are ordered by creation date descending."""
        prompt1 = SystemPrompt.objects.create(
            version='1.0',
            content='First',
            created_by=admin_user
        )
        prompt2 = SystemPrompt.objects.create(
            version='2.0',
            content='Second',
            created_by=admin_user
        )
        
        prompts = list(SystemPrompt.objects.all())
        assert prompts[0] == prompt2
        assert prompts[1] == prompt1


@pytest.mark.unit
@pytest.mark.django_db
class TestLLMLog:
    """Tests for LLMLog model."""
    
    def test_create_llm_log(self, user):
        """Test creating an LLM log."""
        log = LLMLog.create_log(
            user=user,
            user_prompt='Test prompt',
            llm_response='Test response',
            model_name='test-model',
            prompt_version='1.0',
            processing_time_ms=100
        )
        
        assert log.user_hash == hash_user_id(user.username)
        assert log.user_prompt == 'Test prompt'
        assert log.llm_response == 'Test response'
        assert log.model_name == 'test-model'
        assert log.prompt_version == '1.0'
        assert log.processing_time_ms == 100
    
    def test_llm_log_hashes_user_id(self, user):
        """Test that LLM log stores hashed user ID, not plaintext."""
        log = LLMLog.create_log(
            user=user,
            user_prompt='Test',
            llm_response='Response'
        )
        
        # User hash should not be the username
        assert log.user_hash != user.username
        # User hash should be consistent
        assert log.user_hash == hash_user_id(user.username)
    
    def test_str_representation(self, llm_log):
        """Test string representation of LLM log."""
        str_repr = str(llm_log)
        assert 'Log' in str_repr
        assert llm_log.user_hash in str_repr
    
    def test_ordering(self, user):
        """Test that logs are ordered by creation date descending."""
        log1 = LLMLog.create_log(
            user=user,
            user_prompt='First',
            llm_response='Response 1'
        )
        log2 = LLMLog.create_log(
            user=user,
            user_prompt='Second',
            llm_response='Response 2'
        )
        
        logs = list(LLMLog.objects.all())
        assert logs[0] == log2
        assert logs[1] == log1


@pytest.mark.unit
@pytest.mark.django_db
class TestAuditLog:
    """Tests for AuditLog model."""
    
    def test_create_audit_log(self, admin_user, user):
        """Test creating an audit log."""
        log = AuditLog.log_action(
            action='user_created',
            admin=admin_user,
            target_user=user,
            reason='Test creation'
        )
        
        assert log.action == 'user_created'
        assert log.admin == admin_user
        assert log.target_user == user
        assert log.details['reason'] == 'Test creation'
    
    def test_audit_log_without_target_user(self, admin_user):
        """Test creating an audit log without target user."""
        log = AuditLog.log_action(
            action='logs_deleted',
            admin=admin_user,
            count=10
        )
        
        assert log.action == 'logs_deleted'
        assert log.admin == admin_user
        assert log.target_user is None
        assert log.details['count'] == 10
    
    def test_audit_log_without_admin(self, user):
        """Test creating an audit log without admin (system action)."""
        log = AuditLog.log_action(
            action='user_created',
            target_user=user,
            is_initial_setup=True
        )
        
        assert log.action == 'user_created'
        assert log.admin is None
        assert log.target_user == user
    
    def test_str_representation(self, audit_log):
        """Test string representation of audit log."""
        str_repr = str(audit_log)
        assert 'user_created' in str_repr
        assert 'admin' in str_repr.lower()
    
    def test_system_action_str(self, user):
        """Test string representation of system action."""
        log = AuditLog.log_action(
            action='user_created',
            target_user=user
        )
        str_repr = str(log)
        assert 'System' in str_repr
    
    def test_ordering(self, admin_user, user):
        """Test that audit logs are ordered by creation date descending."""
        log1 = AuditLog.log_action(
            action='user_created',
            admin=admin_user,
            target_user=user
        )
        log2 = AuditLog.log_action(
            action='user_disabled',
            admin=admin_user,
            target_user=user
        )
        
        logs = list(AuditLog.objects.all())
        assert logs[0] == log2
        assert logs[1] == log1
