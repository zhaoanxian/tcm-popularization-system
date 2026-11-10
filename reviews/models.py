"""学生4：回复与审核管理"""
import os

from django.contrib.auth.models import User
from django.db import models

from consultations.models import Consultation


class Reply(models.Model):
    """回复记录：针对咨询问题的回复，含审核状态流转"""
    AUDIT_STATUS_CHOICES = [
        ('pending', '待审核'),
        ('approved', '已通过'),
        ('rejected', '已驳回'),
    ]

    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE,
                                     related_name='replies', verbose_name='关联咨询')
    replier = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='replies', verbose_name='回复人')
    reply_content = models.TextField('回复内容')
    audit_status = models.CharField('审核状态', max_length=20,
                                    choices=AUDIT_STATUS_CHOICES, default='pending')
    audit_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='audited_replies', verbose_name='审核人')
    audit_time = models.DateTimeField('审核时间', null=True, blank=True)
    audit_comment = models.CharField('审核意见', max_length=300, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '回复记录'
        verbose_name_plural = '回复记录'
        ordering = ['-created_at']

    def __str__(self):
        return f'回复[{self.id}] - {self.consultation.title[:20]}'


class Attachment(models.Model):
    """附件：异常备注材料 / 回复材料上传"""
    reply = models.ForeignKey(Reply, on_delete=models.CASCADE, null=True, blank=True,
                              related_name='attachments', verbose_name='关联回复')
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, null=True,
                                     blank=True, related_name='attachments',
                                     verbose_name='关联咨询')
    file = models.FileField('附件文件', upload_to='attachments/%Y/%m/')
    filename = models.CharField('原始文件名', max_length=255)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='uploaded_attachments', verbose_name='上传人')
    remark = models.CharField('备注', max_length=300, blank=True)
    created_at = models.DateTimeField('上传时间', auto_now_add=True)

    class Meta:
        verbose_name = '附件'
        verbose_name_plural = '附件'
        ordering = ['-created_at']

    def __str__(self):
        return self.filename

    def save(self, *args, **kwargs):
        if not self.filename and self.file:
            self.filename = os.path.basename(self.file.name)
        super().save(*args, **kwargs)


class ReplyHistory(models.Model):
    """历史记录追踪：记录回复/审核的每次状态流转"""
    reply = models.ForeignKey(Reply, on_delete=models.CASCADE, null=True, blank=True,
                              related_name='histories', verbose_name='关联回复')
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, null=True,
                                     blank=True, related_name='histories',
                                     verbose_name='关联咨询')
    action = models.CharField('动作', max_length=50,
                              help_text='如：创建回复 / 提交审核 / 审核通过 / 审核驳回')
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='reply_histories', verbose_name='操作人')
    detail = models.TextField('变更说明', blank=True)
    created_at = models.DateTimeField('操作时间', auto_now_add=True)

    class Meta:
        verbose_name = '处理历史'
        verbose_name_plural = '处理历史'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.action} @ {self.created_at:%Y-%m-%d %H:%M}'
