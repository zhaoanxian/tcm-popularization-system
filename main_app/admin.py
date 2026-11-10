from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import (Article, Attachment, Category, Consult, Menu, OperationLog,
                     Reply, ReviewLog, Tag, UserProfile)


class ProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = '用户档案'


class UserAdmin(BaseUserAdmin):
    inlines = [ProfileInline]
    list_display = ('username', 'get_role', 'email', 'is_active', 'is_staff')

    @admin.display(description='角色')
    def get_role(self, obj):
        return obj.profile.get_role_display() if hasattr(obj, 'profile') else '-'


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'order', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    search_fields = ('name',)


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'roles', 'order', 'is_active')
    list_editable = ('roles', 'order', 'is_active')


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'author', 'status', 'views', 'is_top', 'created_at')
    list_filter = ('status', 'category', 'is_top')
    search_fields = ('title', 'summary', 'content', 'author')
    filter_horizontal = ('tags',)
    date_hierarchy = 'created_at'


class ReplyInline(admin.TabularInline):
    model = Reply
    extra = 0
    fields = ('reply_no', 'content', 'replier', 'status', 'is_exception')


@admin.register(Consult)
class ConsultAdmin(admin.ModelAdmin):
    list_display = ('consult_no', 'title', 'consult_type', 'asker', 'handler',
                    'status', 'urgency', 'created_at')
    list_filter = ('status', 'consult_type', 'urgency')
    search_fields = ('consult_no', 'title', 'content', 'asker__username')
    inlines = [ReplyInline]


@admin.register(Reply)
class ReplyAdmin(admin.ModelAdmin):
    list_display = ('reply_no', 'consult', 'replier', 'status', 'is_exception', 'created_at')
    list_filter = ('status', 'is_exception')
    search_fields = ('reply_no', 'content')


@admin.register(ReviewLog)
class ReviewLogAdmin(admin.ModelAdmin):
    list_display = ('reply', 'action', 'operator', 'comment', 'created_at')
    list_filter = ('action',)


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('original_name', 'reply', 'uploaded_by', 'uploaded_at')


@admin.register(OperationLog)
class OperationLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'username', 'module', 'action', 'object_type',
                    'detail', 'ip', 'result')
    list_filter = ('module', 'result')
    search_fields = ('username', 'action', 'detail')

    def has_add_permission(self, request):
        return False       # 日志只允许查看
