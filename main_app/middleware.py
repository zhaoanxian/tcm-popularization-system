"""自定义中间件：写操作自动留痕（学生5 第③项 —— 操作日志）。"""
import re

from .permissions import client_ip

# 需要记录的写请求
WRITE_METHODS = ('POST', 'PUT', 'PATCH', 'DELETE')

MODULE_MAP = [
    (r'^/article', 'article'),
    (r'^/consult', 'consult'),
    (r'^/reply', 'reply'),
    (r'^/category', 'category'),
    (r'^/tag', 'category'),
    (r'^/user', 'user'),
    (r'^/stat', 'stat'),
]

ACTION_LABELS = (
    ('delete', '删除'), ('create', '新增'), ('edit', '修改'),
    ('pass', '审核通过'), ('reject', '审核驳回'), ('publish', '发布'),
    ('close', '结案'), ('submit', '提交'), ('upload', '上传附件'),
    ('export', '导出'), ('toggle', '状态切换'),
)


class OperationLogMiddleware:
    """
    说明：视图内已有更精确的日志（含对象编号、字段变化）时，
    会通过 request._log_written = True 告知本中间件不再重复记录。
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            self.record(request, response)
        except Exception:      # 日志失败不能影响业务
            pass
        return response

    def record(self, request, response):
        if request.method not in WRITE_METHODS:
            return
        if getattr(request, '_log_written', False):
            return
        if not getattr(request, 'user', None) or not request.user.is_authenticated:
            return
        if request.path.startswith(('/admin', '/static', '/media')):
            return
        if response.status_code >= 400:
            return

        module = 'article'
        for pattern, mod in MODULE_MAP:
            if re.match(pattern, request.path):
                module = mod
                break

        action = request.path.strip('/').split('/')[0] or 'unknown'
        label = '提交'
        for key, text in ACTION_LABELS:
            if key in request.path:
                label = text
                break
        detail = f'{request.method} {request.path}'
        note = request.POST.get('log_note')
        if note:
            detail = str(note)[:200]

        from .models import OperationLog
        OperationLog.objects.create(
            user=request.user,
            username=request.user.username,
            module=module,
            action=label,
            object_type=request.path.strip('/').split('/')[0],
            detail=detail,
            ip=client_ip(request),
        )
