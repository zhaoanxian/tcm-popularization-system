"""
中医药科普内容与咨询管理系统 —— 数据模型

业务闭环：
    科普文章(Article) — 咨询问题(Consult) — 回复审核(Reply/ReviewLog) — 操作日志(OperationLog)

学生分工对应关系：
    学生1 用户与栏目管理    -> UserProfile / Category / Tag / Menu
    学生2 科普文章管理      -> Article
    学生3 咨询问题管理      -> Consult
    学生4 回复与审核管理    -> Reply / ReviewLog / Attachment
    学生5 检索统计与日志    -> OperationLog
"""
from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from django.utils import timezone


# ---------------------------------------------------------------------------
# 学生1：用户与栏目管理
# ---------------------------------------------------------------------------
ROLE_CHOICES = (
    ('admin', '系统管理员'),
    ('editor', '科普编辑'),
    ('consultant', '咨询医师'),
    ('user', '普通用户'),
)


class UserProfile(models.Model):
    """扩展 Django 内置 User，保存角色、科室、手机号等业务属性。"""
    user = models.OneToOneField(User, on_delete=models.CASCADE,
                                related_name='profile', verbose_name='用户')
    role = models.CharField('角色', max_length=20, choices=ROLE_CHOICES, default='user')
    real_name = models.CharField('真实姓名', max_length=30, blank=True)
    phone = models.CharField('手机号', max_length=20, blank=True)
    department = models.CharField('所属科室', max_length=50, blank=True,
                                  help_text='咨询医师填写，如：中医内科')
    is_active_account = models.BooleanField('账号启用', default=True)
    created_at = models.DateTimeField('注册时间', auto_now_add=True)

    class Meta:
        verbose_name = '用户档案'
        verbose_name_plural = '用户档案'

    def __str__(self):
        return f'{self.display_name}（{self.get_role_display()}）'

    @property
    def display_name(self):
        return self.real_name or self.user.username

    # 便捷判定，供模板与视图使用
    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def can_manage_article(self):
        return self.role in ('admin', 'editor')

    @property
    def can_manage_consult(self):
        return self.role in ('admin', 'consultant')

    @property
    def can_review(self):
        return self.role in ('admin', 'editor')


class Category(models.Model):
    """科普栏目，如：四季养生、中药辨识、穴位保健……"""
    name = models.CharField('栏目名称', max_length=50, unique=True)
    code = models.SlugField('栏目编码', max_length=50, unique=True,
                            help_text='英文小写，用于 URL，如 health-preserve')
    description = models.CharField('栏目简介', max_length=200, blank=True)
    order = models.IntegerField('排序', default=0)
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '科普栏目'
        verbose_name_plural = '科普栏目'
        ordering = ['order', 'id']

    def __str__(self):
        return self.name


class Tag(models.Model):
    """文章标签，如：食疗、艾灸、节气。"""
    name = models.CharField('标签名称', max_length=30, unique=True)
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '标签'
        verbose_name_plural = '标签'
        ordering = ['id']

    def __str__(self):
        return self.name


class Menu(models.Model):
    """菜单与接口权限配置（学生1 第③项）。"""
    name = models.CharField('菜单名称', max_length=50)
    code = models.CharField('权限编码', max_length=50, unique=True,
                            help_text='与装饰器 module_required 使用的编码一致')
    url_name = models.CharField('对应路由名', max_length=100, blank=True)
    icon = models.CharField('图标类名', max_length=50, blank=True, default='bi-grid')
    roles = models.CharField('可见角色', max_length=100, default='admin,editor,consultant,user',
                             help_text='逗号分隔：admin,editor,consultant,user')
    order = models.IntegerField('排序', default=0)
    is_active = models.BooleanField('启用', default=True)

    class Meta:
        verbose_name = '菜单权限'
        verbose_name_plural = '菜单权限'
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.name}({self.code})'

    @property
    def role_list(self):
        return [r.strip() for r in self.roles.split(',') if r.strip()]

    def visible_to(self, role):
        return self.is_active and role in self.role_list


# ---------------------------------------------------------------------------
# 学生2：科普文章管理
# ---------------------------------------------------------------------------
class Article(models.Model):
    STATUS_CHOICES = (
        ('draft', '草稿'),
        ('published', '已发布'),
        ('offline', '已下架'),
    )
    title = models.CharField('文章标题', max_length=120)
    subtitle = models.CharField('副标题', max_length=120, blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT,
                                 related_name='articles', verbose_name='所属栏目')
    tags = models.ManyToManyField(Tag, blank=True, related_name='articles', verbose_name='标签')
    author = models.CharField('作者', max_length=50)
    source = models.CharField('来源', max_length=100, blank=True, default='本站原创')
    summary = models.CharField('摘要', max_length=300, blank=True)
    content = models.TextField('正文')
    cover_image = models.ImageField('封面图', upload_to='article_cover/%Y/%m/', blank=True, null=True)
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='draft')
    is_top = models.BooleanField('是否置顶', default=False)
    views = models.PositiveIntegerField('浏览量', default=0)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='articles', verbose_name='创建人')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    published_at = models.DateTimeField('发布时间', null=True, blank=True)

    class Meta:
        verbose_name = '科普文章'
        verbose_name_plural = '科普文章'
        ordering = ['-is_top', '-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('main_app:article_detail', args=[self.pk])

    def publish(self):
        self.status = 'published'
        if not self.published_at:
            self.published_at = timezone.now()
        self.save(update_fields=['status', 'published_at', 'updated_at'])

    @property
    def status_color(self):
        return {'draft': 'secondary', 'published': 'success', 'offline': 'warning'}.get(self.status, 'secondary')


# ---------------------------------------------------------------------------
# 学生3：咨询问题管理
# ---------------------------------------------------------------------------
class Consult(models.Model):
    TYPE_CHOICES = (
        ('symptom', '症状咨询'),
        ('herb', '中药用法'),
        ('diet', '食疗养生'),
        ('acupoint', '穴位理疗'),
        ('other', '其他'),
    )
    STATUS_CHOICES = (
        ('pending', '待受理'),
        ('processing', '处理中'),
        ('replied', '已回复'),
        ('closed', '已结案'),
    )
    URGENCY_CHOICES = ((1, '普通'), (2, '较急'), (3, '紧急'))

    consult_no = models.CharField('咨询编号', max_length=32, unique=True, editable=False)
    title = models.CharField('咨询标题', max_length=120)
    consult_type = models.CharField('咨询类型', max_length=20, choices=TYPE_CHOICES, default='symptom')
    content = models.TextField('咨询内容')
    urgency = models.PositiveSmallIntegerField('紧急程度', choices=URGENCY_CHOICES, default=1)

    asker = models.ForeignKey(User, on_delete=models.CASCADE,
                              related_name='my_consults', verbose_name='提问用户')
    asker_name = models.CharField('提问人', max_length=30, blank=True)
    asker_gender = models.CharField('性别', max_length=4, blank=True,
                                    choices=(('男', '男'), ('女', '女')))
    asker_age = models.PositiveSmallIntegerField('年龄', null=True, blank=True)
    contact = models.CharField('联系方式', max_length=50, blank=True)

    related_article = models.ForeignKey(Article, on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='consults', verbose_name='关联科普文章')
    handler = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='handled_consults', verbose_name='受理人')
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField('提交时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '咨询问题'
        verbose_name_plural = '咨询问题'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.consult_no} {self.title}'

    def save(self, *args, **kwargs):
        if not self.consult_no:
            today = timezone.now().date().strftime('%Y%m%d')
            seq = Consult.objects.filter(created_at__date=timezone.now().date()).count() + 1
            self.consult_no = f'ZX{today}{seq:04d}'
            while Consult.objects.filter(consult_no=self.consult_no).exists():
                seq += 1
                self.consult_no = f'ZX{today}{seq:04d}'
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('main_app:consult_detail', args=[self.pk])

    @property
    def status_color(self):
        return {'pending': 'danger', 'processing': 'warning',
                'replied': 'primary', 'closed': 'success'}.get(self.status, 'secondary')

    @property
    def latest_reply(self):
        return self.replies.order_by('-created_at').first()

    @property
    def is_reviewed(self):
        """是否已有审核通过的回复（无需额外字段，直接由回复表推导）。"""
        return self.replies.filter(status__in=('approved', 'published')).exists()


# ---------------------------------------------------------------------------
# 学生4：回复与审核管理
# ---------------------------------------------------------------------------
class Reply(models.Model):
    STATUS_CHOICES = (
        ('draft', '草稿'),
        ('submitted', '待审核'),
        ('approved', '审核通过'),
        ('rejected', '审核驳回'),
        ('published', '已发布'),
    )
    consult = models.ForeignKey(Consult, on_delete=models.CASCADE,
                                related_name='replies', verbose_name='所属咨询')
    reply_no = models.CharField('回复编号', max_length=32, unique=True, editable=False)
    content = models.TextField('回复内容')
    replier = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                related_name='replies', verbose_name='回复人')
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='draft')
    is_exception = models.BooleanField('异常备注', default=False)
    exception_note = models.CharField('异常说明', max_length=200, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '咨询回复'
        verbose_name_plural = '咨询回复'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.reply_no}'

    def save(self, *args, **kwargs):
        if not self.reply_no:
            today = timezone.now().date().strftime('%Y%m%d')
            seq = Reply.objects.count() + 1
            self.reply_no = f'HF{today}{seq:04d}'
            while Reply.objects.filter(reply_no=self.reply_no).exists():
                seq += 1
                self.reply_no = f'HF{today}{seq:04d}'
        super().save(*args, **kwargs)

    @property
    def status_color(self):
        return {'draft': 'secondary', 'submitted': 'warning', 'approved': 'info',
                'rejected': 'danger', 'published': 'success'}.get(self.status, 'secondary')


class ReviewLog(models.Model):
    """审核流转记录，同时充当回复的“历史记录追踪”。"""
    ACTION_CHOICES = (
        ('submit', '提交审核'),
        ('pass', '审核通过'),
        ('reject', '审核驳回'),
        ('publish', '发布回复'),
        ('close', '结案'),
        ('reopen', '退回处理'),
    )
    reply = models.ForeignKey(Reply, on_delete=models.CASCADE,
                              related_name='reviews', verbose_name='回复')
    action = models.CharField('操作动作', max_length=20, choices=ACTION_CHOICES)
    comment = models.CharField('审核意见', max_length=300, blank=True)
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                 related_name='review_logs', verbose_name='操作人')
    created_at = models.DateTimeField('操作时间', auto_now_add=True)

    class Meta:
        verbose_name = '审核记录'
        verbose_name_plural = '审核记录'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.reply.reply_no}-{self.get_action_display()}'


def attachment_upload_to(instance, filename):
    return f'attachment/{timezone.now():%Y/%m}/{filename}'


class Attachment(models.Model):
    """回复附件（图片/PDF），学生4 第③项。"""
    reply = models.ForeignKey(Reply, on_delete=models.CASCADE,
                              related_name='attachments', verbose_name='所属回复')
    file = models.FileField('附件', upload_to=attachment_upload_to)
    original_name = models.CharField('原文件名', max_length=200, blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='attachments', verbose_name='上传人')
    uploaded_at = models.DateTimeField('上传时间', auto_now_add=True)

    class Meta:
        verbose_name = '回复附件'
        verbose_name_plural = '回复附件'

    def __str__(self):
        return self.original_name or self.file.name


# ---------------------------------------------------------------------------
# 学生5：检索统计与日志
# ---------------------------------------------------------------------------
class OperationLog(models.Model):
    MODULE_CHOICES = (
        ('auth', '登录认证'),
        ('user', '用户管理'),
        ('category', '栏目管理'),
        ('article', '科普文章'),
        ('consult', '咨询问题'),
        ('reply', '回复审核'),
        ('stat', '统计检索'),
    )
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name='operation_logs', verbose_name='操作人')
    username = models.CharField('操作人账号', max_length=150, blank=True)
    module = models.CharField('业务模块', max_length=20, choices=MODULE_CHOICES, default='article')
    action = models.CharField('操作类型', max_length=30)
    object_type = models.CharField('业务对象', max_length=50, blank=True)
    object_id = models.CharField('对象编号', max_length=50, blank=True)
    detail = models.CharField('操作说明', max_length=300, blank=True)
    ip = models.CharField('IP 地址', max_length=50, blank=True)
    result = models.CharField('结果', max_length=10, default='success',
                              choices=(('success', '成功'), ('fail', '失败')))
    created_at = models.DateTimeField('操作时间', auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = '操作日志'
        verbose_name_plural = '操作日志'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['module', 'created_at'])]

    def __str__(self):
        return f'{self.username}-{self.action}-{self.created_at:%Y-%m-%d %H:%M}'

    def save(self, *args, **kwargs):
        if self.user_id and not self.username:
            self.username = self.user.username
        super().save(*args, **kwargs)
