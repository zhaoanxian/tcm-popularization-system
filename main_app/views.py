"""
视图层 —— 按 5 个功能包分区，每个视图前标注对应学生与子功能编号。
路由命名统一前缀 main_app:
"""
import csv
import io
import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (ArticleForm, AttachmentForm, CategoryForm, ConsultAdminForm,
                    ConsultForm, LoginForm, RegisterForm, ReplyForm,
                    ReviewForm, TagForm)
from .models import (Article, Attachment, Category, Consult, Menu, OperationLog,
                     Reply, ReviewLog, Tag, UserProfile)
from .permissions import (client_ip, get_profile, module_required, role_of,
                          role_required, write_log)

PAGE_SIZE = 10


def paginate(request, queryset, size=PAGE_SIZE):
    paginator = Paginator(queryset, size)
    return paginator.get_page(request.GET.get('page'))


def querystring(request, **kwargs):
    """保留当前查询条件生成分页链接，剔除 page 参数。"""
    params = request.GET.copy()
    params.pop('page', None)
    for k, v in kwargs.items():
        params[k] = v
    return params.urlencode()


# ===========================================================================
# 首页
# ===========================================================================
def index(request):
    ctx = {
        'total_article': Article.objects.filter(status='published').count(),
        'total_consult': Consult.objects.count(),
        'pending_consult': Consult.objects.filter(status__in=('pending', 'processing')).count(),
        'pending_reply': Reply.objects.filter(status='submitted').count(),
        'latest_articles': Article.objects.filter(status='published').select_related('category')[:6],
        'categories': Category.objects.filter(is_active=True).annotate(
            num=Count('articles', filter=Q(articles__status='published'))),
    }
    if request.user.is_authenticated:
        role = role_of(request.user)
        if role in ('admin', 'editor'):
            ctx['my_consults'] = Consult.objects.exclude(status='closed').select_related('asker')[:5]
        elif role == 'consultant':
            ctx['my_consults'] = Consult.objects.filter(
                Q(handler=request.user) | Q(handler__isnull=True)).exclude(
                status='closed').select_related('asker')[:5]
        else:
            ctx['my_consults'] = Consult.objects.filter(asker=request.user)[:5]
    return render(request, 'index.html', ctx)


# ===========================================================================
# 学生1 用户与栏目管理
# ===========================================================================
def register_view(request):
    """① 用户注册"""
    if request.user.is_authenticated:
        return redirect('main_app:index')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        write_log(request, 'auth', '注册', 'User', user.pk, f'新用户注册：{user.username}')
        messages.success(request, '注册成功，请登录。')
        return redirect('main_app:login')
    return render(request, 'user/register.html', {'form': form})


def login_view(request):
    """① 登录（不同角色登录后进入同一个首页，但菜单不同）"""
    if request.user.is_authenticated:
        return redirect('main_app:index')
    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        username = form.cleaned_data['username']
        user = authenticate(request, username=username,
                            password=form.cleaned_data['password'])
        if user is None:
            messages.error(request, '账号或密码错误。')
            OperationLog.objects.create(username=username, module='auth',
                                        action='登录失败', ip=client_ip(request),
                                        result='fail', detail='账号或密码错误')
        elif not user.is_active:
            messages.error(request, '该账号已被停用，请联系管理员。')
        else:
            login(request, user)
            profile, _ = UserProfile.objects.get_or_create(user=user)
            OperationLog.objects.create(
                user=user, username=user.username, module='auth', action='登录',
                object_type='User', object_id=str(user.pk), ip=client_ip(request),
                detail=f'{profile.display_name} 以 {role_of(user)} 身份登录')
            messages.success(request, f'欢迎回来，{profile.display_name}！')
            return redirect(request.GET.get('next') or 'main_app:index')
    return render(request, 'user/login.html', {'form': form})


@login_required
def logout_view(request):
    """① 退出"""
    OperationLog.objects.create(
        user=request.user, username=request.user.username, module='auth',
        action='退出', object_type='User', object_id=str(request.user.pk),
        ip=client_ip(request), detail='用户退出登录')
    logout(request)
    messages.info(request, '已安全退出。')
    return redirect('main_app:login')


@login_required
def profile_view(request):
    """① 个人信息"""
    prof, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        prof.real_name = request.POST.get('real_name', '').strip()
        prof.phone = request.POST.get('phone', '').strip()
        prof.department = request.POST.get('department', '').strip()
        prof.save()
        request.user.email = request.POST.get('email', '').strip()
        request.user.save(update_fields=['email'])
        write_log(request, 'user', '修改资料', 'UserProfile', prof.pk, '修改个人资料')
        messages.success(request, '资料已更新。')
        return redirect('main_app:profile')
    return render(request, 'user/profile.html', {'prof': prof})


@role_required('admin')
@module_required('user_manage')
def user_list(request):
    """② 管理员用户管理 + 角色分配"""
    kw = request.GET.get('kw', '').strip()
    role = request.GET.get('role', '')
    qs = UserProfile.objects.select_related('user').order_by('-created_at')
    if kw:
        qs = qs.filter(Q(user__username__icontains=kw) | Q(real_name__icontains=kw)
                       | Q(phone__icontains=kw))
    if role:
        qs = qs.filter(role=role)
    return render(request, 'user/list.html', {
        'page_obj': paginate(request, qs), 'kw': kw, 'role': role,
        'role_choices': UserProfile._meta.get_field('role').choices,
        'qs': querystring(request),
    })


@role_required('admin')
@module_required('user_manage')
def user_role_edit(request, pk):
    """② 角色修改 / 启用停用"""
    prof = get_object_or_404(UserProfile, pk=pk)
    if request.method == 'POST':
        new_role = request.POST.get('role')
        if new_role in dict(UserProfile._meta.get_field('role').choices):
            old = prof.get_role_display()
            prof.role = new_role
            prof.is_active_account = request.POST.get('is_active_account') == 'on'
            prof.save()
            prof.user.is_staff = new_role == 'admin'
            prof.user.is_active = prof.is_active_account
            prof.user.save(update_fields=['is_staff', 'is_active'])
            write_log(request, 'user', '角色调整', 'UserProfile', prof.pk,
                      f'{prof.user.username}: {old} -> {prof.get_role_display()}')
            messages.success(request, '角色已更新。')
    return redirect('main_app:user_list')


@role_required('admin')
@module_required('category_manage')
def category_list(request):
    """③ 栏目维护"""
    form = CategoryForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        write_log(request, 'category', '新增栏目', 'Category', obj.pk, f'新增栏目：{obj.name}')
        messages.success(request, '栏目已新增。')
        return redirect('main_app:category_list')
    qs = Category.objects.annotate(num=Count('articles'))
    return render(request, 'category/list.html', {'form': form, 'rows': qs})


@role_required('admin')
@module_required('category_manage')
def category_edit(request, pk):
    obj = get_object_or_404(Category, pk=pk)
    form = CategoryForm(request.POST or None, instance=obj)
    if request.method == 'POST' and form.is_valid():
        form.save()
        write_log(request, 'category', '修改栏目', 'Category', obj.pk, f'修改栏目：{obj.name}')
        messages.success(request, '栏目已保存。')
        return redirect('main_app:category_list')
    return render(request, 'category/edit.html', {'form': form, 'obj': obj})


@role_required('admin')
@module_required('category_manage')
def category_delete(request, pk):
    obj = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        if obj.articles.exists():
            messages.error(request, '该栏目下还有文章，不能删除，请先下架或转移。')
        else:
            name = obj.name
            obj.delete()
            write_log(request, 'category', '删除栏目', 'Category', pk, f'删除栏目：{name}')
            messages.success(request, '栏目已删除。')
    return redirect('main_app:category_list')


@role_required('admin')
@module_required('category_manage')
def tag_list(request):
    """③ 标签维护"""
    form = TagForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        write_log(request, 'category', '新增标签', 'Tag', obj.pk, f'新增标签：{obj.name}')
        messages.success(request, '标签已新增。')
        return redirect('main_app:tag_list')
    return render(request, 'category/tag_list.html', {
        'form': form, 'rows': Tag.objects.annotate(num=Count('articles'))})


@role_required('admin')
@module_required('category_manage')
def tag_delete(request, pk):
    if request.method == 'POST':
        obj = get_object_or_404(Tag, pk=pk)
        name = obj.name
        obj.delete()
        write_log(request, 'category', '删除标签', 'Tag', pk, f'删除标签：{name}')
        messages.success(request, '标签已删除。')
    return redirect('main_app:tag_list')


@role_required('admin')
@module_required('menu_config')
def menu_config(request):
    """③ 角色、菜单与接口访问权限配置"""
    menus = Menu.objects.all()
    if request.method == 'POST':
        menu = get_object_or_404(Menu, pk=request.POST.get('menu_id'))
        roles = request.POST.getlist('roles')
        menu.roles = ','.join(roles) or 'admin'
        menu.is_active = request.POST.get('is_active') == 'on'
        menu.save()
        write_log(request, 'user', '菜单权限配置', 'Menu', menu.pk,
                  f'{menu.name} 可见角色 -> {menu.roles}')
        messages.success(request, f'「{menu.name}」权限已保存。')
        return redirect('main_app:menu_config')
    return render(request, 'user/menu_config.html', {
        'menus': menus,
        'all_roles': UserProfile._meta.get_field('role').choices,
    })


# ===========================================================================
# 学生2 科普文章管理
# ===========================================================================
def article_list(request):
    """③ 列表分页 + 关键字/条件筛选"""
    kw = request.GET.get('kw', '').strip()
    cat = request.GET.get('category', '')
    tag = request.GET.get('tag', '')
    status = request.GET.get('status', '')
    start = request.GET.get('start', '')
    end = request.GET.get('end', '')

    is_staff_editor = role_of(request.user) in ('admin', 'editor')
    qs = Article.objects.select_related('category').prefetch_related('tags')
    # 普通用户只能看到已发布文章；编辑/管理员可看全部
    if not is_staff_editor:
        qs = qs.filter(status='published')

    if kw:
        qs = qs.filter(Q(title__icontains=kw) | Q(summary__icontains=kw)
                       | Q(content__icontains=kw) | Q(author__icontains=kw))
    if cat:
        qs = qs.filter(category__code=cat)
    if tag:
        qs = qs.filter(tags__name=tag)
    if status and is_staff_editor:
        qs = qs.filter(status=status)
    if start:
        qs = qs.filter(created_at__date__gte=start)
    if end:
        qs = qs.filter(created_at__date__lte=end)

    return render(request, 'article/list.html', {
        'page_obj': paginate(request, qs.distinct()),
        'categories': Category.objects.filter(is_active=True),
        'tags': Tag.objects.filter(is_active=True),
        'kw': kw, 'cat': cat, 'tag': tag, 'status': status,
        'start': start, 'end': end, 'qs': querystring(request),
        'can_edit': is_staff_editor,
        'status_choices': Article.STATUS_CHOICES,
    })


def article_detail(request, pk):
    """② 详情查看"""
    obj = get_object_or_404(Article.objects.select_related('category'), pk=pk)
    can_edit = role_of(request.user) in ('admin', 'editor')
    if obj.status != 'published' and not can_edit:
        messages.warning(request, '该文章尚未发布。')
        return redirect('main_app:article_list')
    Article.objects.filter(pk=pk).update(views=obj.views + 1)
    obj.views += 1
    return render(request, 'article/detail.html', {
        'obj': obj,
        'can_edit': can_edit,
        'related': Article.objects.filter(category=obj.category, status='published')
                                   .exclude(pk=obj.pk)[:5],
        'consults': obj.consults.all()[:5] if can_edit else None,
    })


@role_required('admin', 'editor')
@module_required('article_manage')
def article_create(request):
    """① 新增"""
    form = ArticleForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        if obj.status == 'published':
            obj.published_at = timezone.now()
        obj.save()
        form.save_m2m()
        request._log_written = True
        write_log(request, 'article', '新增文章', 'Article', obj.pk, f'新增科普文章：{obj.title}')
        messages.success(request, '文章已新增。')
        return redirect('main_app:article_detail', pk=obj.pk)
    return render(request, 'article/form.html', {'form': form, 'title': '新增科普文章'})


@role_required('admin', 'editor')
@module_required('article_manage')
def article_edit(request, pk):
    """② 编辑"""
    obj = get_object_or_404(Article, pk=pk)
    form = ArticleForm(request.POST or None, request.FILES or None, instance=obj)
    if request.method == 'POST' and form.is_valid():
        old_status = obj.status
        obj = form.save(commit=False)
        if obj.status == 'published' and old_status != 'published':
            obj.published_at = timezone.now()
        obj.save()
        form.save_m2m()
        request._log_written = True
        write_log(request, 'article', '编辑文章', 'Article', obj.pk,
                  f'编辑科普文章：{obj.title}')
        messages.success(request, '文章已保存。')
        return redirect('main_app:article_detail', pk=obj.pk)
    return render(request, 'article/form.html', {
        'form': form, 'title': '编辑科普文章', 'obj': obj})


@role_required('admin', 'editor')
@module_required('article_manage')
def article_delete(request, pk):
    """② 删除"""
    obj = get_object_or_404(Article, pk=pk)
    if request.method == 'POST':
        title = obj.title
        obj.delete()
        write_log(request, 'article', '删除文章', 'Article', pk, f'删除科普文章：{title}')
        messages.success(request, '文章已删除。')
    return redirect('main_app:article_list')


@role_required('admin', 'editor')
@module_required('article_manage')
def article_toggle_status(request, pk):
    """② 状态流转：发布 / 下架"""
    obj = get_object_or_404(Article, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'publish':
            obj.publish()
        elif action == 'offline':
            obj.status = 'offline'
            obj.save(update_fields=['status', 'updated_at'])
        write_log(request, 'article', '状态变更', 'Article', obj.pk,
                  f'{obj.title} -> {obj.get_status_display()}')
        messages.success(request, '状态已更新。')
    return redirect(request.META.get('HTTP_REFERER') or '/article/')


# ===========================================================================
# 学生3 咨询问题管理
# ===========================================================================
@login_required
@module_required('consult_manage')
def consult_list(request):
    """③ 记录查询与状态查看"""
    role = role_of(request.user)
    kw = request.GET.get('kw', '').strip()
    status = request.GET.get('status', '')
    ctype = request.GET.get('type', '')
    urgency = request.GET.get('urgency', '')
    mine = request.GET.get('mine', '')

    qs = Consult.objects.select_related('asker', 'handler', 'related_article')
    if role == 'user':
        qs = qs.filter(asker=request.user)          # 普通用户仅看自己的
    if kw:
        qs = qs.filter(Q(consult_no__icontains=kw) | Q(title__icontains=kw)
                       | Q(content__icontains=kw) | Q(asker_name__icontains=kw))
    if status:
        qs = qs.filter(status=status)
    if ctype:
        qs = qs.filter(consult_type=ctype)
    if urgency:
        qs = qs.filter(urgency=urgency)
    if mine == '1' and role in ('admin', 'consultant'):
        qs = qs.filter(handler=request.user)

    return render(request, 'consult/list.html', {
        'page_obj': paginate(request, qs),
        'kw': kw, 'status': status, 'ctype': ctype, 'urgency': urgency, 'mine': mine,
        'status_choices': Consult.STATUS_CHOICES,
        'type_choices': Consult.TYPE_CHOICES,
        'urgency_choices': Consult.URGENCY_CHOICES,
        'can_handle': role in ('admin', 'consultant'),
        'qs': querystring(request),
    })


@login_required
@module_required('consult_manage')
def consult_create(request):
    """① 业务记录创建"""
    initial = {}
    art_id = request.GET.get('article')
    if art_id:
        initial['related_article'] = art_id
    form = ConsultForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.asker = request.user
        prof = get_profile(request.user)
        obj.asker_name = obj.asker_name or (prof.display_name if prof else request.user.username)
        obj.save()
        request._log_written = True
        write_log(request, 'consult', '新增咨询', 'Consult', obj.pk,
                  f'提交咨询：{obj.consult_no} {obj.title}')
        messages.success(request, f'咨询已提交，编号 {obj.consult_no}，请等待医师回复。')
        return redirect('main_app:consult_detail', pk=obj.pk)
    return render(request, 'consult/form.html', {'form': form})


@login_required
@module_required('consult_manage')
def consult_detail(request, pk):
    """② 明细数据维护 / 状态查看"""
    obj = get_object_or_404(Consult.objects.select_related('asker', 'handler'), pk=pk)
    role = role_of(request.user)
    if role == 'user' and obj.asker_id != request.user.id:
        messages.error(request, '您只能查看自己提交的咨询。')
        return redirect('main_app:consult_list')
    return render(request, 'consult/detail.html', {
        'obj': obj,
        'replies': obj.replies.select_related('replier')
                              .prefetch_related('reviews__operator', 'attachments'),
        'can_handle': role in ('admin', 'consultant'),
        'can_review': role in ('admin', 'editor'),
        'is_owner': obj.asker_id == request.user.id,
    })


@login_required
@module_required('consult_manage')
def consult_edit(request, pk):
    """② 维护明细（受理人、状态、内容修正）"""
    obj = get_object_or_404(Consult, pk=pk)
    role = role_of(request.user)
    if role not in ('admin', 'consultant'):
        messages.error(request, '仅咨询医师/管理员可维护咨询明细。')
        return redirect('main_app:consult_detail', pk=pk)
    form = ConsultAdminForm(request.POST or None, instance=obj)
    if request.method == 'POST' and form.is_valid():
        old = Consult.objects.get(pk=pk).status
        new_obj = form.save(commit=False)
        if new_obj.handler_id is None and new_obj.status in ('processing', 'replied'):
            new_obj.handler = request.user
        new_obj.save()
        request._log_written = True
        write_log(request, 'consult', '维护咨询', 'Consult', obj.pk,
                  f'{obj.consult_no} 状态 {old} -> {new_obj.status}')
        messages.success(request, '咨询信息已更新。')
        return redirect('main_app:consult_detail', pk=pk)
    return render(request, 'consult/form.html', {'form': form, 'obj': obj})


@role_required('admin', 'consultant')
@module_required('consult_manage')
def consult_claim(request, pk):
    """③ 受理（状态置为处理中并绑定受理人）"""
    obj = get_object_or_404(Consult, pk=pk)
    if request.method == 'POST' and obj.status == 'pending':
        obj.handler = request.user
        obj.status = 'processing'
        obj.save(update_fields=['handler', 'status', 'updated_at'])
        write_log(request, 'consult', '受理咨询', 'Consult', obj.pk,
                  f'受理 {obj.consult_no}')
        messages.success(request, '已受理，状态更新为「处理中」。')
    return redirect('main_app:consult_detail', pk=pk)


@role_required('admin', 'consultant')
@module_required('consult_manage')
def consult_close(request, pk):
    obj = get_object_or_404(Consult, pk=pk)
    if request.method == 'POST':
        obj.status = 'closed'
        obj.save(update_fields=['status', 'updated_at'])
        write_log(request, 'consult', '结案', 'Consult', obj.pk, f'{obj.consult_no} 结案')
        messages.success(request, '咨询已结案。')
    return redirect('main_app:consult_detail', pk=pk)


# ===========================================================================
# 学生4 回复与审核管理
# ===========================================================================
@login_required
@module_required('reply_manage')
def reply_task_list(request):
    """① 待办任务：待回复咨询 / 待审核回复"""
    role = role_of(request.user)
    tab = request.GET.get('tab', 'task')

    if tab == 'review':
        qs = Reply.objects.filter(status='submitted').select_related('consult', 'replier')
    elif tab == 'history':
        qs = Reply.objects.exclude(status='draft').select_related('consult', 'replier')
    else:  # task：待我回复
        qs = Consult.objects.filter(status__in=('pending', 'processing'))
        if role == 'consultant':
            qs = qs.filter(Q(handler=request.user) | Q(handler__isnull=True))
        qs = qs.select_related('asker', 'handler')

    kw = request.GET.get('kw', '').strip()
    if kw:
        if tab in ('review', 'history'):
            qs = qs.filter(Q(consult__consult_no__icontains=kw)
                           | Q(consult__title__icontains=kw) | Q(reply_no__icontains=kw))
        else:
            qs = qs.filter(Q(consult_no__icontains=kw) | Q(title__icontains=kw))

    return render(request, 'reply/task_list.html', {
        'page_obj': paginate(request, qs), 'tab': tab, 'kw': kw,
        'can_reply': role in ('admin', 'consultant'),
        'can_review': role in ('admin', 'editor'),
        'stat': {
            'pending': Consult.objects.filter(status__in=('pending', 'processing')).count(),
            'review': Reply.objects.filter(status='submitted').count(),
            'done': Reply.objects.filter(status='published').count(),
        },
        'qs': querystring(request),
    })


@role_required('admin', 'consultant')
@module_required('reply_manage')
def reply_create(request, consult_id):
    """① 回复处理：写回复并提交审核"""
    consult = get_object_or_404(Consult, pk=consult_id)
    if consult.status == 'closed':
        messages.warning(request, '该咨询已结案，如需继续答复请先退回处理。')
        return redirect('main_app:consult_detail', pk=consult.pk)

    form = ReplyForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        reply = form.save(commit=False)
        reply.consult = consult
        reply.replier = request.user
        reply.status = 'submitted'
        reply.save()
        ReviewLog.objects.create(reply=reply, action='submit', operator=request.user,
                                 comment='提交审核')
        if consult.status in ('pending', 'processing'):
            consult.status = 'replied'
            if not consult.handler_id:
                consult.handler = request.user
            consult.save(update_fields=['status', 'handler', 'updated_at'])
        request._log_written = True
        write_log(request, 'reply', '提交回复', 'Reply', reply.pk,
                  f'{reply.reply_no} 针对咨询 {consult.consult_no}')
        messages.success(request, '回复已提交审核，等待编辑审核通过后发布。')
        return redirect('main_app:consult_detail', pk=consult.pk)
    return render(request, 'reply/form.html', {'form': form, 'consult': consult})


@role_required('admin', 'editor', 'consultant')
@module_required('reply_manage')
def reply_detail(request, pk):
    """② 审核 / ③ 历史记录追踪 + 附件"""
    reply = get_object_or_404(Reply.objects.select_related('consult', 'replier'), pk=pk)
    role = role_of(request.user)
    att_form = AttachmentForm()
    if request.method == 'POST' and request.POST.get('form_type') == 'upload':
        att_form = AttachmentForm(request.POST, request.FILES)
        if att_form.is_valid():
            att = att_form.save(commit=False)
            att.reply = reply
            att.original_name = request.FILES['file'].name
            att.uploaded_by = request.user
            att.save()
            request._log_written = True
            write_log(request, 'reply', '上传附件', 'Reply', reply.pk,
                      f'{reply.reply_no} 上传附件 {att.original_name}')
            messages.success(request, '附件已上传。')
            return redirect('main_app:reply_detail', pk=pk)
    return render(request, 'reply/detail.html', {
        'reply': reply,
        'reviews': reply.reviews.select_related('operator'),
        'attachments': reply.attachments.all(),
        'att_form': att_form,
        'review_form': ReviewForm(),
        'can_review': role in ('admin', 'editor'),
        'can_publish': role in ('admin', 'editor'),
        'can_edit': role == 'admin' or reply.replier_id == request.user.id,
    })


@role_required('admin', 'editor')
@module_required('reply_manage')
def reply_review(request, pk):
    """② 审核通过 / 驳回 / 发布 / 结案"""
    reply = get_object_or_404(Reply.objects.select_related('consult'), pk=pk)
    if request.method != 'POST':
        return redirect('main_app:reply_detail', pk=pk)

    action = request.POST.get('action')
    comment = request.POST.get('comment', '').strip()
    consult = reply.consult

    if action == 'pass':
        if reply.status != 'submitted':
            messages.error(request, '只有「待审核」的回复可以通过审核。')
            return redirect('main_app:reply_detail', pk=pk)
        reply.status = 'approved'
        reply.save(update_fields=['status', 'updated_at'])
        ReviewLog.objects.create(reply=reply, action='pass', operator=request.user,
                                 comment=comment or '审核通过')
        messages.success(request, '审核通过，可执行「发布」。')

    elif action == 'reject':
        if not comment:
            messages.error(request, '驳回必须填写审核意见。')
            return redirect('main_app:reply_detail', pk=pk)
        reply.status = 'rejected'
        reply.save(update_fields=['status', 'updated_at'])
        ReviewLog.objects.create(reply=reply, action='reject', operator=request.user,
                                 comment=comment)
        consult.status = 'processing'
        consult.save(update_fields=['status', 'updated_at'])
        messages.warning(request, '已驳回，咨询退回处理中。')

    elif action == 'publish':
        if reply.status != 'approved':
            messages.error(request, '需先审核通过才能发布。')
            return redirect('main_app:reply_detail', pk=pk)
        reply.status = 'published'
        reply.save(update_fields=['status', 'updated_at'])
        ReviewLog.objects.create(reply=reply, action='publish', operator=request.user,
                                 comment=comment or '发布给用户')
        messages.success(request, '回复已发布，用户可查看。')

    elif action in ('close', 'reopen'):
        consult.status = 'closed' if action == 'close' else 'processing'
        consult.save(update_fields=['status', 'updated_at'])
        ReviewLog.objects.create(reply=reply, action=action, operator=request.user,
                                 comment=comment or dict(ReviewLog.ACTION_CHOICES)[action])
        messages.success(request, '咨询状态已更新。')

    request._log_written = True
    write_log(request, 'reply', dict(ReviewLog.ACTION_CHOICES).get(action, action),
              'Reply', reply.pk, f'{reply.reply_no} {comment[:80]}')
    return redirect('main_app:reply_detail', pk=reply.pk)


# ===========================================================================
# 学生5 检索统计与日志
# ===========================================================================
@login_required
def search_view(request):
    """① 按时间 / 人员 / 业务对象多条件查询（跨表联合检索）"""
    role = role_of(request.user)
    if role == 'user':
        messages.warning(request, '综合检索面向工作人员开放。')
        return redirect('main_app:index')

    kw = request.GET.get('kw', '').strip()
    obj_type = request.GET.get('obj_type', '')
    user_id = request.GET.get('user_id', '')
    start = request.GET.get('start', '')
    end = request.GET.get('end', '')
    module = request.GET.get('module', '')

    results = []
    if request.GET:
        if obj_type in ('', 'article'):
            qs = Article.objects.all()
            if kw:
                qs = qs.filter(Q(title__icontains=kw) | Q(content__icontains=kw))
            if user_id:
                qs = qs.filter(created_by_id=user_id)
            if start:
                qs = qs.filter(created_at__date__gte=start)
            if end:
                qs = qs.filter(created_at__date__lte=end)
            results += [{'type': '科普文章', 'no': f'A{a.pk}', 'title': a.title,
                         'owner': a.created_by.username if a.created_by else a.author,
                         'status': a.get_status_display(), 'time': a.created_at,
                         'url': f'/article/{a.pk}/'} for a in qs[:100]]

        if obj_type in ('', 'consult'):
            qs = Consult.objects.select_related('asker', 'handler')
            if kw:
                qs = qs.filter(Q(consult_no__icontains=kw) | Q(title__icontains=kw)
                               | Q(content__icontains=kw))
            if user_id:
                qs = qs.filter(Q(asker_id=user_id) | Q(handler_id=user_id))
            if start:
                qs = qs.filter(created_at__date__gte=start)
            if end:
                qs = qs.filter(created_at__date__lte=end)
            results += [{'type': '咨询问题', 'no': c.consult_no, 'title': c.title,
                         'owner': c.asker.username, 'status': c.get_status_display(),
                         'time': c.created_at, 'url': f'/consult/{c.pk}/'} for c in qs[:100]]

        if obj_type in ('', 'reply'):
            qs = Reply.objects.select_related('consult', 'replier')
            if kw:
                qs = qs.filter(Q(reply_no__icontains=kw) | Q(content__icontains=kw))
            if user_id:
                qs = qs.filter(replier_id=user_id)
            if start:
                qs = qs.filter(created_at__date__gte=start)
            if end:
                qs = qs.filter(created_at__date__lte=end)
            results += [{'type': '咨询回复', 'no': r.reply_no, 'title': r.consult.title,
                         'owner': r.replier.username if r.replier else '-',
                         'status': r.get_status_display(), 'time': r.created_at,
                         'url': f'/reply/{r.pk}/'} for r in qs[:100]]

        if obj_type in ('', 'log'):
            qs = OperationLog.objects.all()
            if kw:
                qs = qs.filter(Q(detail__icontains=kw) | Q(action__icontains=kw))
            if user_id:
                qs = qs.filter(user_id=user_id)
            if module:
                qs = qs.filter(module=module)
            if start:
                qs = qs.filter(created_at__date__gte=start)
            if end:
                qs = qs.filter(created_at__date__lte=end)
            results += [{'type': '操作日志', 'no': f'L{l.pk}', 'title': l.detail or l.action,
                         'owner': l.username, 'status': l.get_result_display(),
                         'time': l.created_at, 'url': '/stat/log/'} for l in qs[:100]]

        results.sort(key=lambda x: x['time'], reverse=True)
        write_log(request, 'stat', '综合检索', 'Query', '',
                  f'条件 kw={kw} type={obj_type} user={user_id} {start}~{end}，命中 {len(results)} 条')

    return render(request, 'stat/search.html', {
        'results': results[:200], 'kw': kw, 'obj_type': obj_type, 'user_id': user_id,
        'start': start, 'end': end, 'module': module,
        'users': User.objects.filter(profile__role__in=('admin', 'editor', 'consultant')),
        'modules': OperationLog.MODULE_CHOICES,
        'obj_types': (('article', '科普文章'), ('consult', '咨询问题'),
                      ('reply', '咨询回复'), ('log', '操作日志')),
        'searched': bool(request.GET),
    })


@login_required
@role_required('admin', 'editor')
def stat_dashboard(request):
    """② 检索统计：Pandas 汇总 + ECharts 图表"""
    import pandas as pd

    today = timezone.now().date()
    try:
        days = max(7, min(int(request.GET.get('days', 14)), 90))
    except ValueError:
        days = 14
    start = today - timedelta(days=days - 1)
    end = today

    art_df = pd.DataFrame(list(Article.objects.filter(created_at__date__range=(start, end))
                               .values('created_at')))
    con_df = pd.DataFrame(list(Consult.objects.filter(created_at__date__range=(start, end))
                               .values('created_at', 'consult_type', 'status')))
    rep_df = pd.DataFrame(list(Reply.objects.filter(created_at__date__range=(start, end))
                               .values('created_at', 'status')))
    for df in (art_df, con_df, rep_df):
        if not df.empty:
            df['date'] = pd.to_datetime(df['created_at']).dt.strftime('%m-%d')

    date_index = [(start + timedelta(days=i)).strftime('%m-%d') for i in range(days)]

    def series(df):
        if df.empty:
            return [0] * len(date_index)
        g = df.groupby('date').size()
        return [int(g.get(d, 0)) for d in date_index]

    cat_data = list(Article.objects.filter(status='published')
                    .values('category__name').annotate(v=Count('id')).order_by('-v'))
    type_data = list(Consult.objects.values('consult_type').annotate(v=Count('id')).order_by('-v'))
    type_label = dict(Consult.TYPE_CHOICES)
    work_data = list(Consult.objects.filter(handler__isnull=False)
                     .values('handler__username')
                     .annotate(total=Count('id'), done=Count('id', filter=Q(status='closed')))
                     .order_by('-total')[:10])
    reply_status = list(Reply.objects.values('status').annotate(v=Count('id')))
    reply_label = dict(Reply.STATUS_CHOICES)

    stats = {
        'article': Article.objects.count(),
        'published': Article.objects.filter(status='published').count(),
        'consult': Consult.objects.count(),
        'pending': Consult.objects.filter(status__in=('pending', 'processing')).count(),
        'reply_pending': Reply.objects.filter(status='submitted').count(),
        'pass_rate': round(Reply.objects.filter(status__in=('approved', 'published')).count()
                           / max(Reply.objects.exclude(status='draft').count(), 1) * 100, 1),
    }

    chart = {
        'dates': date_index,
        'article_series': series(art_df),
        'consult_series': series(con_df),
        'reply_series': series(rep_df),
        'cat_names': [c['category__name'] for c in cat_data],
        'cat_values': [c['v'] for c in cat_data],
        'type_names': [type_label.get(t['consult_type'], t['consult_type']) for t in type_data],
        'type_values': [t['v'] for t in type_data],
        'work_names': [w['handler__username'] for w in work_data],
        'work_totals': [w['total'] for w in work_data],
        'work_done': [w['done'] for w in work_data],
        'reply_names': [reply_label.get(r['status'], r['status']) for r in reply_status],
        'reply_values': [r['v'] for r in reply_status],
    }

    table = []
    if not con_df.empty:
        agg = con_df.groupby('consult_type').size().reset_index(name='数量')
        agg['类型'] = agg['consult_type'].map(type_label)
        table = agg[['类型', '数量']].sort_values('数量', ascending=False).to_dict('records')

    report_rows = []
    for c in Category.objects.all():
        total = c.articles.count()
        pub = c.articles.filter(status='published').count()
        report_rows.append({'name': c.name, 'total': total, 'pub': pub,
                            'rate': round(pub / total * 100, 1) if total else 0})

    return render(request, 'stat/dashboard.html', {
        'stats': stats, 'chart_json': json.dumps(chart, ensure_ascii=False),
        'days': days, 'start': start, 'end': end,
        'table': table, 'report_rows': report_rows,
    })


@login_required
@role_required('admin', 'editor')
def log_list(request):
    """③ 操作日志查询"""
    qs = OperationLog.objects.select_related('user')
    kw = request.GET.get('kw', '').strip()
    module = request.GET.get('module', '')
    start = request.GET.get('start', '')
    end = request.GET.get('end', '')
    if kw:
        qs = qs.filter(Q(username__icontains=kw) | Q(action__icontains=kw)
                       | Q(detail__icontains=kw))
    if module:
        qs = qs.filter(module=module)
    if start:
        qs = qs.filter(created_at__date__gte=start)
    if end:
        qs = qs.filter(created_at__date__lte=end)
    return render(request, 'stat/log_list.html', {
        'page_obj': paginate(request, qs), 'kw': kw, 'module': module,
        'start': start, 'end': end, 'modules': OperationLog.MODULE_CHOICES,
        'qs': querystring(request),
    })


@login_required
@role_required('admin', 'editor')
def export_csv(request):
    """③ 结果导出（CSV，UTF-8 BOM 防 Excel 中文乱码）"""
    target = request.GET.get('target', 'consult')
    qs_start = request.GET.get('start', '')
    qs_end = request.GET.get('end', '')

    buf = io.StringIO()
    writer = csv.writer(buf)
    if target == 'article':
        writer.writerow(['ID', '标题', '栏目', '作者', '状态', '浏览量', '创建时间'])
        qs = Article.objects.select_related('category')
        if qs_start:
            qs = qs.filter(created_at__date__gte=qs_start)
        if qs_end:
            qs = qs.filter(created_at__date__lte=qs_end)
        for a in qs:
            writer.writerow([a.pk, a.title, a.category.name, a.author,
                             a.get_status_display(), a.views,
                             a.created_at.strftime('%Y-%m-%d %H:%M')])
    elif target == 'log':
        writer.writerow(['ID', '操作人', '模块', '操作', '对象', '说明', 'IP', '结果', '时间'])
        for l in OperationLog.objects.all()[:5000]:
            writer.writerow([l.pk, l.username, l.get_module_display(), l.action,
                             l.object_type, l.detail, l.ip, l.get_result_display(),
                             l.created_at.strftime('%Y-%m-%d %H:%M:%S')])
    else:
        writer.writerow(['咨询编号', '标题', '类型', '提问人', '受理人', '状态',
                         '紧急程度', '提交时间'])
        qs = Consult.objects.select_related('asker', 'handler')
        if qs_start:
            qs = qs.filter(created_at__date__gte=qs_start)
        if qs_end:
            qs = qs.filter(created_at__date__lte=qs_end)
        for c in qs:
            writer.writerow([c.consult_no, c.title, c.get_consult_type_display(),
                             c.asker.username,
                             c.handler.username if c.handler else '',
                             c.get_status_display(), c.get_urgency_display(),
                             c.created_at.strftime('%Y-%m-%d %H:%M')])

    write_log(request, 'stat', '导出数据', 'Export', target, f'导出 {target} 数据')
    resp = HttpResponse('\ufeff' + buf.getvalue(), content_type='text/csv; charset=utf-8')
    resp['Content-Disposition'] = (
        f'attachment; filename="{target}_{timezone.now().date():%Y%m%d}.csv"')
    return resp


@login_required
@role_required('admin', 'editor')
def print_view(request, target='consult'):
    """③ 打印页面（浏览器 Ctrl+P 打印/存 PDF）"""
    if target == 'article':
        rows = Article.objects.select_related('category')[:100]
        headers = ['ID', '标题', '栏目', '作者', '状态', '浏览']
        data = [[a.pk, a.title, a.category.name, a.author, a.get_status_display(), a.views]
                for a in rows]
    elif target == 'log':
        rows = OperationLog.objects.all()[:100]
        headers = ['时间', '操作人', '模块', '操作', '说明']
        data = [[l.created_at.strftime('%Y-%m-%d %H:%M'), l.username,
                 l.get_module_display(), l.action, l.detail] for l in rows]
    else:
        rows = Consult.objects.select_related('asker', 'handler')[:100]
        headers = ['编号', '标题', '提问人', '受理人', '状态', '时间']
        data = [[c.consult_no, c.title, c.asker.username,
                 c.handler.username if c.handler else '', c.get_status_display(),
                 c.created_at.strftime('%Y-%m-%d %H:%M')] for c in rows]

    return render(request, 'stat/print.html', {
        'headers': headers, 'data': data, 'target': target,
        'now': timezone.now(),
        'title': {'article': '科普文章清单',
                  'log': '操作日志清单'}.get(target, '咨询问题清单'),
    })


# -------------------------- 接口：AJAX 小功能 --------------------------
def api_category_options(request):
    """前端联动的接口示例（演示接口级权限）"""
    if role_of(request.user) not in ('admin', 'editor'):
        return JsonResponse({'ok': False, 'msg': '无权限'}, status=403)
    data = [{'id': c.pk, 'name': c.name} for c in Category.objects.filter(is_active=True)]
    return JsonResponse({'ok': True, 'data': data})


def api_consult_status(request):
    """咨询状态轮询接口（用户详情页用）"""
    if not request.user.is_authenticated:
        return JsonResponse({'ok': False, 'msg': '请先登录'}, status=403)
    c = Consult.objects.filter(pk=request.GET.get('id')).first()
    if not c:
        return JsonResponse({'ok': False, 'msg': '记录不存在'}, status=404)
    return JsonResponse({'ok': True, 'status': c.get_status_display(),
                         'status_key': c.status,
                         'updated': c.updated_at.strftime('%Y-%m-%d %H:%M')})
