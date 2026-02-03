"""
Database models for AI Describer Medical core application.
"""
import hmac
import hashlib
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings


def hash_user_id(username: str) -> str:
    """
    Hash user ID using HMAC-SHA256 for privacy.
    Returns first 16 characters of the hash.
    """
    secret = settings.HMAC_SECRET or 'PLEASE_SET_HMAC_SECRET_IN_ENV_FILE'
    return hmac.new(
        secret.encode(),
        username.encode(),
        hashlib.sha256
    ).hexdigest()[:16]


class SystemPrompt(models.Model):
    """
    System prompts for LLM processing.
    Only one prompt can be active at a time.
    """
    version = models.CharField(max_length=20, unique=True)
    content = models.TextField()
    is_active = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_prompts'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'system_prompts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"v{self.version} {'(Active)' if self.is_active else ''}"
    
    def save(self, *args, **kwargs):
        """Ensure only one prompt is active at a time."""
        if self.is_active:
            # Deactivate all other prompts
            SystemPrompt.objects.filter(is_active=True).update(is_active=False)
        super().save(*args, **kwargs)


class LLMLog(models.Model):
    """
    Logs of LLM processing requests and responses.
    User information is hashed for privacy.
    """
    user_hash = models.CharField(max_length=16, db_index=True)
    user_prompt = models.TextField()
    llm_response = models.TextField()
    model_name = models.CharField(max_length=100, blank=True)
    prompt_version = models.CharField(max_length=20, blank=True)
    processing_time_ms = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'llm_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user_hash', 'created_at']),
        ]
    
    def __str__(self):
        return f"Log {self.id} - {self.user_hash} at {self.created_at}"
    
    @classmethod
    def create_log(cls, user, user_prompt, llm_response, **kwargs):
        """
        Create a new log entry with hashed user ID.
        """
        return cls.objects.create(
            user_hash=hash_user_id(user.username),
            user_prompt=user_prompt,
            llm_response=llm_response,
            **kwargs
        )


class AuditLog(models.Model):
    """
    Audit logs for administrative actions.
    """
    ACTION_CHOICES = [
        ('user_created', 'User Created'),
        ('user_disabled', 'User Disabled'),
        ('user_password_reset', 'User Password Reset'),
        ('logs_deleted', 'Logs Deleted'),
        ('prompt_created', 'Prompt Created'),
        ('prompt_updated', 'Prompt Updated'),
        ('prompt_activated', 'Prompt Activated'),
    ]
    
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    admin = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_actions'
    )
    target_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_targets'
    )
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']
    
    def __str__(self):
        admin_name = self.admin.username if self.admin else 'System'
        return f"{self.action} by {admin_name} at {self.created_at}"
    
    @classmethod
    def log_action(cls, action, admin=None, target_user=None, **details):
        """
        Create a new audit log entry.
        """
        return cls.objects.create(
            action=action,
            admin=admin,
            target_user=target_user,
            details=details
        )
