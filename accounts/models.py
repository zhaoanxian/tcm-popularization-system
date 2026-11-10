"""学生1：用户与栏目管理 —— 角色、菜单、用户资料、栏目、标签"""
from django.contrib.auth.models import User
from django.db import models


class Role(models.Model):
    """角色：系统管理员 / 内容管理员 / 普通用户"""
    name = models.CharField('角色名称', max_length=50, unique=True)
    code = models.CharField('角色编码', max_length=50, unique=True,
                            help_text='如 admin / editor / user')
    description = models.TextField('角色说明', blank=True)
    is_system = models.BooleanField('系统内置', default=False)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '角色'
        verbose_name_plural = '角色'
        ordering = ['id']

    def __str__(self):
        return self.name


class Menu(models.Model):
    """系统菜单：用于侧边栏展示与接口访问权限控制"""
    name = models.CharField('菜单名称', max_length=50)
    url = models.CharField('菜单地址', max_length=200,
                           help_text='如 /articles/ ，中间件按地址前缀匹配权限')
    icon = models.CharField('图标样式', max_length=50, blank=True,
                            help_text='Bootstrap Icons 类名，如 bi-journal-text')
    parent = models.ForeignKey('self', null=True, blank=True,
                               on_delete=models.CASCADE, verbose_name='父级菜单')
    sort_order = models.IntegerField('排序号', default=0)
    is_visible = models.BooleanField('是否显示', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '菜单'
        verbose_name_plural = '菜单'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.name


class RoleMenu(models.Model):
    """角色-菜单访问权限配置"""
    role = models.ForeignKey(Role, on_delete=models.CASCADE, verbose_name='角色')
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, verbose_name='菜单')
    can_access = models.BooleanField('允许访问', default=True)

    class Meta:
        verbose_name = '角色菜单权限'
        verbose_name_plural = '角色菜单权限'
        unique_together = ('role', 'menu')

    def __str__(self):
        return f'{self.role.name} - {self.menu.name}'


class UserProfile(models.Model):
    """用户资料：关联角色、真实姓名、联系电话"""
    user = models.OneToOneField(User, on_delete=models.CASCADE,
                                related_name='profile', verbose_name='用户')
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name='users', verbose_name='角色')
    real_name = models.CharField('真实姓名', max_length=50, blank=True)
    phone = models.CharField('联系电话', max_length=20, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '用户资料'
        verbose_name_plural = '用户资料'

    def __str__(self):
        return f'{self.user.username}({self.role.name if self.role else "未分配"})'

    def role_code(self):
        return self.role.code if self.role else ''


class Column(models.Model):
    """科普文章栏目（分类）"""
    name = models.CharField('栏目名称', max_length=100, unique=True)
    slug = models.SlugField('栏目标识', max_length=100, unique=True)
    description = models.TextField('栏目说明', blank=True)
    sort_order = models.IntegerField('排序号', default=0)
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '栏目'
        verbose_name_plural = '栏目'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.name


class Tag(models.Model):
    """科普文章标签"""
    name = models.CharField('标签名称', max_length=50, unique=True)
    slug = models.SlugField('标签标识', max_length=50, unique=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '标签'
        verbose_name_plural = '标签'
        ordering = ['id']

    def __str__(self):
        return self.name
