"""
统一权限与日志工具（学生1 第③项 / 学生5 第③项）
"""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect

from .models import OperationLog, UserProfile


def get_profile(user):
    """安全获取 UserProfile，老数据没有 profile 时自动补建。"""
    if not user.is_authenticated:
        return None
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


def role_of(user):
    if not user.is_authenticated:
        return 'anonymous'
    if user.is_superuser:
        return 'admin'
    p = get_profile(user)
    return p.role if p else 'user'


def role_required(*roles):
    """角色校验装饰器：不满足时 403（接口）或跳回首页（页面）。"""
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if role_of(request.user) in roles:
                return view_func(request, *args, **kwargs)
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'ok': False, 'msg': '无访问权限'}, status=403)
            messages.error(request, '您当前的角色（%s）无权访问该功能。' % role_of(request.user))
            return HttpResponseForbidden(
                '<h3 style="font-family:sans-serif;padding:40px">403 无访问权限，'
                '<a href="/">返回首页</a></h3>')
        return _wrapped
    return decorator


def module_required(code):
    """按 Menu 表中的接口/菜单配置动态判断权限（数据库驱动，可后台调整）。"""
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            from .models import Menu
            menu = Menu.objects.filter(code=code).first()
            if menu is None or menu.visible_to(role_of(request.user)):
                return view_func(request, *args, **kwargs)
            messages.error(request, '当前角色未开通该菜单权限。')
            return redirect('main_app:index')
        return _wrapped
    return decorator


def client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def write_log(request, module, action, object_type='', object_id='', detail='', result='success'):
    """写一条操作日志。"""
    user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
    OperationLog.objects.create(
        user=user,
        username=user.username if user else request.POST.get('username', ''),
        module=module,
        action=action,
        object_type=object_type,
        object_id=str(object_id or ''),
        detail=detail[:300],
        ip=client_ip(request),
        result=result,
    )
