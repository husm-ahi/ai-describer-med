"""
Views for core application.
"""
import json
import logging
import secrets

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.core.paginator import Paginator
from django.conf import settings

logger = logging.getLogger(__name__)

User = get_user_model()


def generate_random_password():
    """
    Generate a cryptographically secure random password.
    Uses settings.PASSWORD_GEN_LENGTH and settings.PASSWORD_GEN_CHARS.
    """
    length = settings.PASSWORD_GEN_LENGTH
    chars = settings.PASSWORD_GEN_CHARS
    
    # Generate cryptographically secure random password without modulo bias
    password = ''.join(secrets.choice(chars) for _ in range(length))
    
    return password


def staff_required(view_func):
    """
    Decorator for views that checks that the user is staff.
    """
    decorated_view = user_passes_test(
        lambda user: user.is_active and user.is_staff,
        login_url='/accounts/login/'
    )(view_func)
    return decorated_view


def index(request):
    """
    Main page for voice input and QR code generation.
    Requires authentication.
    """
    if not request.user.is_authenticated:
        return redirect('account_login')
    
    return render(request, 'core/index.html', {
        'user': request.user,
    })


def setup(request):
    """
    Initial setup page for creating the first admin user.
    Only accessible when no user exists at all.
    """
    # Close setup as soon as any user exists. Checking only for superusers
    # would reopen this unauthenticated page whenever no superuser remains.
    if User.objects.exists():
        return redirect('/admin-dashboard/')
    
    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()
        password = request.POST.get('password') or ''
        password_confirm = request.POST.get('password_confirm') or ''
        
        if not username:
            return render(request, 'core/setup.html', {
                'error': 'ユーザー名を入力してください。'
            })
        
        # Validate password confirmation
        if password != password_confirm:
            return render(request, 'core/setup.html', {
                'error': 'パスワードが一致しません。'
            })
        
        # Validate password length
        if len(password) < 8:
            return render(request, 'core/setup.html', {
                'error': 'パスワードは8文字以上で設定してください。'
            })
        
        # Create superuser
        try:
            user = User.objects.create_superuser(
                username=username,
                password=password,
            )
            
            # Log the action
            from .models import AuditLog, SystemPrompt
            AuditLog.log_action(
                action='user_created',
                admin=user,
                target_user=user,
                is_initial_setup=True
            )
            
            # Create default system prompt if no prompts exist
            import os
            from django.conf import settings
            
            if SystemPrompt.objects.count() == 0:
                try:
                    default_prompt_path = os.path.join(
                        settings.BASE_DIR,
                        'backend',
                        'core',
                        'default_prompts',
                        'system_prompt_default.txt'
                    )
                    
                    with open(default_prompt_path, 'r', encoding='utf-8') as f:
                        default_content = f.read()
                    
                    SystemPrompt.objects.create(
                        version='v1.0.0',
                        content=default_content,
                        created_by=user,
                        is_active=True
                    )
                except Exception as prompt_error:
                    # Log error but don't fail user creation
                    logger.error(f"デフォルトプロンプト作成エラー: {prompt_error}", exc_info=True)
            
            # Auto login the created user
            from django.contrib.auth import login
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            
            return redirect('/admin-dashboard/')
        except Exception as e:
            logger.error(f"初期管理者作成エラー: {e}", exc_info=True)
            return render(request, 'core/setup.html', {
                'error': 'ユーザーの作成に失敗しました。'
            })
    
    return render(request, 'core/setup.html')


# Note: LLM processing is now handled exclusively via WebSocket (see consumers.py)
# The HTTP endpoint has been removed to simplify the codebase and improve security.


# ============================================================================
# Admin Dashboard Views
# ============================================================================

@staff_required
def admin_dashboard(request):
    """
    Admin dashboard overview page.
    """
    from .models import SystemPrompt, LLMLog, AuditLog
    
    # Get statistics
    active_prompt = SystemPrompt.objects.filter(is_active=True).first()
    total_logs = LLMLog.objects.count()
    total_users = User.objects.filter(is_active=True).count()
    recent_audit_logs = AuditLog.objects.select_related('admin', 'target_user').order_by('-created_at')[:10]
    
    context = {
        'active_prompt': active_prompt,
        'total_logs': total_logs,
        'total_users': total_users,
        'recent_audit_logs': recent_audit_logs,
    }
    
    return render(request, 'core/admin_dashboard.html', context)


@staff_required
@require_http_methods(["GET"])
def generate_password_api(request):
    """
    API endpoint to generate a random password.
    Returns a suggested password that admin can use or modify.
    """
    password = generate_random_password()
    return JsonResponse({'password': password})


@staff_required
def manage_prompts(request):
    """
    System prompt management page.
    """
    from .models import SystemPrompt, AuditLog
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            version = request.POST.get('version')
            content = request.POST.get('content')
            
            prompt = SystemPrompt.objects.create(
                version=version,
                content=content,
                created_by=request.user,
                is_active=False
            )
            
            AuditLog.log_action(
                action='prompt_created',
                admin=request.user,
                version=version
            )
            
            return JsonResponse({'success': True, 'id': prompt.id})
        
        elif action == 'update':
            prompt_id = request.POST.get('prompt_id')
            version = request.POST.get('version')
            content = request.POST.get('content')
            
            prompt = get_object_or_404(SystemPrompt, id=prompt_id)
            prompt.version = version
            prompt.content = content
            prompt.save()
            
            AuditLog.log_action(
                action='prompt_updated',
                admin=request.user,
                version=version
            )
            
            return JsonResponse({'success': True})
        
        elif action == 'activate':
            prompt_id = request.POST.get('prompt_id')
            prompt = get_object_or_404(SystemPrompt, id=prompt_id)
            
            # Deactivate all others
            SystemPrompt.objects.exclude(id=prompt_id).update(is_active=False)
            prompt.is_active = True
            prompt.save()
            
            AuditLog.log_action(
                action='prompt_activated',
                admin=request.user,
                version=prompt.version
            )
            
            return JsonResponse({'success': True})
        
        elif action == 'delete':
            prompt_id = request.POST.get('prompt_id')
            prompt = get_object_or_404(SystemPrompt, id=prompt_id)
            
            if prompt.is_active:
                return JsonResponse({'error': '有効なプロンプトは削除できません'}, status=400)
            
            version = prompt.version
            prompt.delete()
            
            AuditLog.log_action(
                action='prompt_deleted',
                admin=request.user,
                version=version
            )
            
            return JsonResponse({'success': True})
    
    # GET request
    prompts = SystemPrompt.objects.select_related('created_by').order_by('-created_at')
    
    return render(request, 'core/manage_prompts.html', {
        'prompts': prompts
    })


@staff_required
def load_default_prompt(request):
    """
    Load default system prompt from file.
    """
    import os
    from django.conf import settings
    
    try:
        # Path to default prompt file
        default_prompt_path = os.path.join(
            settings.BASE_DIR,
            'backend',
            'core',
            'default_prompts',
            'system_prompt_default.txt'
        )
        
        with open(default_prompt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return JsonResponse({'success': True, 'content': content})
    except FileNotFoundError:
        return JsonResponse({'error': 'デフォルトプロンプトファイルが見つかりません'}, status=404)
    except Exception as e:
        logger.error(f"デフォルトプロンプト読み込みエラー: {e}", exc_info=True)
        return JsonResponse({'error': 'ファイル読み込みエラー'}, status=500)


@staff_required
def view_logs(request):
    """
    LLM logs viewing page with search and filtering.
    """
    from .models import LLMLog
    
    # Get filter parameters
    search_query = request.GET.get('q', '')
    model_filter = request.GET.get('model', '')
    version_filter = request.GET.get('version', '')
    page_number = request.GET.get('page', 1)
    
    # Build query
    logs = LLMLog.objects.all()
    
    if search_query:
        logs = logs.filter(
            Q(user_hash__icontains=search_query) |
            Q(user_prompt__icontains=search_query) |
            Q(llm_response__icontains=search_query)
        )
    
    if model_filter:
        logs = logs.filter(model_name=model_filter)
    
    if version_filter:
        logs = logs.filter(prompt_version=version_filter)
    
    logs = logs.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(logs, 50)  # 50 logs per page
    page_obj = paginator.get_page(page_number)
    
    # Get unique models and versions for filters
    models = LLMLog.objects.values_list('model_name', flat=True).distinct()
    versions = LLMLog.objects.values_list('prompt_version', flat=True).distinct()
    
    return render(request, 'core/view_logs.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'model_filter': model_filter,
        'version_filter': version_filter,
        'models': models,
        'versions': versions,
    })


@staff_required
def manage_users(request):
    """
    User management page.
    """
    from .models import AuditLog
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            username = request.POST.get('username')
            role = request.POST.get('role', 'user')  # user, staff (superuser is not allowed)
            
            # Validate username
            if not username or len(username) < 3:
                return JsonResponse({'error': 'ユーザー名は3文字以上で入力してください'}, status=400)
            
            if User.objects.filter(username=username).exists():
                return JsonResponse({'error': 'このユーザー名は既に使用されています'}, status=400)
            
            # Ignore superuser role - only allow 'user' or 'staff'
            if role not in ['user', 'staff']:
                role = 'user'
            
            # Generate random password on server side
            password = generate_random_password()
            
            # Create user (never create superuser from web UI)
            try:
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    is_staff=(role == 'staff'),
                    is_active=True
                )
                
                AuditLog.log_action(
                    action='user_created',
                    admin=request.user,
                    target_user=user
                )
                
                return JsonResponse({
                    'success': True,
                    'password': password  # Return generated password to display to admin
                })
            except Exception as e:
                logger.error(f"ユーザー作成エラー: {e}", exc_info=True)
                return JsonResponse({'error': 'ユーザー作成に失敗しました'}, status=500)
        
        elif action == 'disable':
            user_id = request.POST.get('user_id')
            user = get_object_or_404(User, id=user_id)
            
            if user.is_superuser:
                return JsonResponse({'error': 'スーパーユーザーは無効化できません'}, status=400)
            
            # Disable user
            random_password = secrets.token_urlsafe(48)
            user.set_password(random_password)
            user.is_active = False
            user.save()
            
            AuditLog.log_action(
                action='user_disabled',
                admin=request.user,
                target_user=user
            )
            
            return JsonResponse({'success': True})
        
        elif action == 'enable':
            user_id = request.POST.get('user_id')
            user = get_object_or_404(User, id=user_id)
            
            user.is_active = True
            user.save()
            
            AuditLog.log_action(
                action='user_enabled',
                admin=request.user,
                target_user=user
            )
            
            return JsonResponse({'success': True})
        
        elif action == 'reset_password':
            user_id = request.POST.get('user_id')
            password = request.POST.get('password')
            user = get_object_or_404(User, id=user_id)
            
            if user.is_superuser and user.id != request.user.id:
                return JsonResponse({'error': '他の管理者のパスワードは変更できません'}, status=400)
            
            if not password:
                return JsonResponse({'error': 'パスワードを入力してください'}, status=400)
            
            try:
                validate_password(password, user=user)
            except ValidationError as e:
                return JsonResponse({'error': ' '.join(e.messages)}, status=400)
            
            # Use password from admin (generated or modified)
            user.set_password(password)
            user.save()
            
            AuditLog.log_action(
                action='password_reset',
                admin=request.user,
                target_user=user
            )
            
            return JsonResponse({'success': True})
        
        elif action == 'promote_to_staff':
            user_id = request.POST.get('user_id')
            user = get_object_or_404(User, id=user_id)
            
            # superuserに対して実行すると is_superuser が外れてしまうため拒否
            if user.is_superuser:
                return JsonResponse({'error': '管理者（superuser）は変更できません'}, status=400)
            
            # 一般ユーザー → スタッフ
            user.is_staff = True
            user.is_superuser = False
            user.save()
            
            AuditLog.log_action(
                action='user_promoted_to_staff',
                admin=request.user,
                target_user=user
            )
            
            return JsonResponse({'success': True})
        
        elif action == 'demote_to_user':
            user_id = request.POST.get('user_id')
            user = get_object_or_404(User, id=user_id)
            
            # superuserは降格不可
            if user.is_superuser:
                return JsonResponse({'error': '管理者（superuser）を降格することはできません'}, status=400)
            
            # スタッフ → 一般ユーザー
            user.is_staff = False
            user.save()
            
            AuditLog.log_action(
                action='user_demoted_to_user',
                admin=request.user,
                target_user=user
            )
            
            return JsonResponse({'success': True})
    
    # GET request
    users = User.objects.all().order_by('-date_joined')
    
    return render(request, 'core/manage_users.html', {
        'users': users
    })
