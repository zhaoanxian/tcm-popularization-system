"""模板上下文处理器：把“当前用户可见的菜单”注入所有模板。"""
from .models import Menu

ROLE_LABELS = {
    'admin': '系统管理员',
    'editor': '科普编辑',
    'consultant': '咨询医师',
    'user': '普通用户',
    'anonymous': '游客',
}


def menu_permissions(request):
    user = getattr(request, 'user', None)
    role = 'anonymous'
    profile = None
    if user and user.is_authenticated:
        if user.is_superuser:
            role = 'admin'
        else:
            profile = getattr(user, 'profile', None)
            role = profile.role if profile else 'user'

    menus = [m for m in Menu.objects.filter(is_active=True) if m.visible_to(role)]
    return {
        'nav_menus': menus,
        'current_role': role,
        'current_role_label': ROLE_LABELS.get(role, role),
        'profile': profile,
    }
