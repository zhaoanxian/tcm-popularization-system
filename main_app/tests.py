"""
单元测试 —— 按 5 名学生分工组织，每人 3 组用例。
运行：python manage.py test main_app -v 2
"""
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from .models import (Article, Category, Consult, Menu, OperationLog, Reply,
                     ReviewLog, Tag, UserProfile)

PWD = 'tcm123456'


def make_user(username, role):
    u = User.objects.create_user(username=username, password=PWD)
    UserProfile.objects.create(user=u, role=role, real_name=username)
    return u


class BaseCase(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name='四季养生', code='health-preserve')
        self.tag = Tag.objects.create(name='食疗')
        self.admin = make_user('admin01', 'admin')
        self.editor = make_user('editor01', 'editor')
        self.doctor = make_user('doctor01', 'consultant')
        self.normal = make_user('user01', 'user')
        Menu.objects.create(name='回复审核', code='reply_manage',
                            url_name='main_app:reply_task_list',
                            roles='admin,editor,consultant')

    def login(self, username):
        self.client.login(username=username, password=PWD)


# ===========================================================================
# 学生1 用户与栏目管理
# ===========================================================================
class Student1UserTest(BaseCase):
    """① 注册 / 登录 / 退出"""

    def test_register_success(self):
        """TC1-1 注册成功后自动生成 UserProfile，默认角色为普通用户"""
        resp = self.client.post(reverse('main_app:register'), {
            'username': 'newuser', 'real_name': '新用户', 'phone': '13900000000',
            'email': 'a@b.com', 'role': 'user',
            'password1': 'Zhongyi@2025', 'password2': 'Zhongyi@2025'})
        self.assertEqual(resp.status_code, 302)
        u = User.objects.get(username='newuser')
        self.assertEqual(u.profile.role, 'user')
        self.assertEqual(u.profile.real_name, '新用户')

    def test_register_password_mismatch(self):
        """TC1-2 两次密码不一致时留在注册页并提示"""
        resp = self.client.post(reverse('main_app:register'), {
            'username': 'baduser', 'real_name': '张三', 'role': 'user',
            'password1': 'Zhongyi@2025', 'password2': 'Other@2025'})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(username='baduser').exists())

    def test_login_logout_and_log(self):
        """TC1-3 登录成功写入操作日志，退出后回到登录页"""
        self.client.post(reverse('main_app:login'),
                         {'username': 'user01', 'password': PWD})
        self.assertTrue(OperationLog.objects.filter(
            username='user01', action='登录').exists())
        resp = self.client.get(reverse('main_app:logout'))
        self.assertRedirects(resp, reverse('main_app:login'))

    def test_login_wrong_password_logged(self):
        """TC1-4 密码错误不登录，且记录失败日志"""
        self.client.post(reverse('main_app:login'),
                         {'username': 'user01', 'password': 'wrong'})
        self.assertFalse(self.client.session.get('_auth_user_id'))
        self.assertTrue(OperationLog.objects.filter(result='fail').exists())


class Student1RoleTest(BaseCase):
    """② 角色与栏目 / 标签维护"""

    def test_category_crud_by_admin(self):
        """TC1-5 管理员新增栏目 + 编辑 + 删除"""
        self.login('admin01')
        self.client.post(reverse('main_app:category_list'),
                         {'name': '穴位保健', 'code': 'acupoint', 'order': 3, 'is_active': 'on'})
        c = Category.objects.get(code='acupoint')
        self.client.post(reverse('main_app:category_edit', args=[c.pk]),
                         {'name': '穴位保健', 'code': 'acupoint', 'order': 5, 'is_active': 'on'})
        self.assertEqual(Category.objects.get(pk=c.pk).order, 5)
        self.client.post(reverse('main_app:category_delete', args=[c.pk]))
        self.assertFalse(Category.objects.filter(pk=c.pk).exists())

    def test_category_delete_blocked_when_has_article(self):
        """TC1-6 栏目下有文章时禁止删除（PROTECT 保护）"""
        Article.objects.create(title='测试文章标题', category=self.cat, author='王',
                               content='正文', status='published')
        self.login('admin01')
        self.client.post(reverse('main_app:category_delete', args=[self.cat.pk]))
        self.assertTrue(Category.objects.filter(pk=self.cat.pk).exists())

    def test_editor_cannot_manage_category(self):
        """TC1-7 编辑访问栏目管理被拒绝（403）"""
        self.login('editor01')
        resp = self.client.get(reverse('main_app:category_list'))
        self.assertEqual(resp.status_code, 403)

    def test_tag_create(self):
        """TC1-8 标签新增"""
        self.login('admin01')
        self.client.post(reverse('main_app:tag_list'), {'name': '艾灸', 'is_active': 'on'})
        self.assertTrue(Tag.objects.filter(name='艾灸').exists())


class Student1PermissionTest(BaseCase):
    """③ 角色、菜单与接口访问权限配置"""

    def test_role_change_effect(self):
        """TC1-9 把普通用户改为编辑后即可访问文章新增页"""
        self.login('admin01')
        self.client.post(reverse('main_app:user_role_edit', args=[self.normal.profile.pk]),
                         {'role': 'editor', 'is_active_account': 'on'})
        self.assertEqual(UserProfile.objects.get(user=self.normal).role, 'editor')
        self.client.logout()
        self.login('user01')
        resp = self.client.get(reverse('main_app:article_create'))
        self.assertEqual(resp.status_code, 200)

    def test_menu_permission_blocks_view(self):
        """TC1-10 关闭菜单权限后，访问对应视图被重定向回首页"""
        menu = Menu.objects.get(code='reply_manage')
        menu.roles = 'admin,editor'
        menu.save()
        self.login('doctor01')
        resp = self.client.get(reverse('main_app:reply_task_list'))
        self.assertRedirects(resp, reverse('main_app:index'))

    def test_api_permission(self):
        """TC1-11 接口级权限：普通用户调用分类接口返回 403 JSON"""
        self.login('user01')
        resp = self.client.get(reverse('main_app:api_categories'))
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(resp.json()['ok'])
        self.client.logout()
        self.login('editor01')
        self.assertEqual(self.client.get(reverse('main_app:api_categories')).status_code, 200)


# ===========================================================================
# 学生2 科普文章管理
# ===========================================================================
class Student2ArticleTest(BaseCase):
    """① 新增"""

    def test_create_article(self):
        """TC2-1 编辑新增文章，自动绑定创建人、状态为已发布"""
        self.login('editor01')
        resp = self.client.post(reverse('main_app:article_create'), {
            'title': '足三里保健详解', 'category': self.cat.pk, 'author': '李时珍',
            'content': '足三里定位与按揉方法……', 'summary': '摘要', 'status': 'published',
            'source': '本站原创', 'tags': [self.tag.pk]})
        self.assertEqual(resp.status_code, 302)
        a = Article.objects.get(title='足三里保健详解')
        self.assertEqual(a.created_by, self.editor)
        self.assertIsNotNone(a.published_at)
        self.assertEqual(a.tags.count(), 1)

    def test_title_too_short(self):
        """TC2-2 标题少于 4 字时校验失败"""
        self.login('editor01')
        resp = self.client.post(reverse('main_app:article_create'), {
            'title': '短', 'category': self.cat.pk, 'author': '李', 'content': '正文内容'})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Article.objects.filter(title='短').exists())


class Student2EditTest(BaseCase):
    """② 编辑 / 删除 / 详情"""

    def setUp(self):
        super().setUp()
        self.art = Article.objects.create(title='初识黄芪', category=self.cat,
                                          author='李时珍', content='黄芪正文', status='published')

    def test_edit_and_detail(self):
        """TC2-3 编辑标题后详情页展示新标题，浏览量 +1"""
        self.login('editor01')
        self.client.post(reverse('main_app:article_edit', args=[self.art.pk]), {
            'title': '初识黄芪（修订版）', 'category': self.cat.pk, 'author': '李时珍',
            'content': '黄芪正文', 'status': 'published', 'source': '本站原创'})
        self.art.refresh_from_db()
        self.assertIn('修订版', self.art.title)
        self.client.get(reverse('main_app:article_detail', args=[self.art.pk]))
        self.art.refresh_from_db()
        self.assertEqual(self.art.views, 1)

    def test_delete_article(self):
        """TC2-4 删除文章后数据库不再存在"""
        self.login('admin01')
        self.client.post(reverse('main_app:article_delete', args=[self.art.pk]))
        self.assertFalse(Article.objects.filter(pk=self.art.pk).exists())

    def test_offline_status(self):
        """TC2-5 下架后普通用户看不到该文章"""
        self.login('editor01')
        self.client.post(reverse('main_app:article_toggle', args=[self.art.pk]),
                         {'action': 'offline'})
        self.art.refresh_from_db()
        self.assertEqual(self.art.status, 'offline')
        self.client.logout()
        resp = self.client.get(reverse('main_app:article_detail', args=[self.art.pk]))
        self.assertRedirects(resp, reverse('main_app:article_list'))


class Student2ListTest(BaseCase):
    """③ 列表分页与筛选"""

    def setUp(self):
        super().setUp()
        cat2 = Category.objects.create(name='中药辨识', code='herb')
        for i in range(15):
            Article.objects.create(title=f'科普文章第{i}篇', category=self.cat if i % 2 else cat2,
                                   author='李时珍', content='内容', summary='黄芪黄芪',
                                   status='published' if i % 3 else 'draft')

    def test_pagination(self):
        """TC2-6 每页 10 条，共 2 页"""
        self.login('editor01')
        resp = self.client.get(reverse('main_app:article_list'))
        self.assertEqual(len(resp.context['page_obj']), 10)
        self.assertEqual(resp.context['page_obj'].paginator.num_pages, 2)

    def test_filter_by_keyword(self):
        """TC2-7 关键字检索命中 15 条"""
        self.login('editor01')
        resp = self.client.get(reverse('main_app:article_list'), {'kw': '黄芪'})
        self.assertEqual(resp.context['page_obj'].paginator.count, 15)

    def test_filter_by_category_and_status(self):
        """TC2-8 栏目 + 状态组合筛选"""
        self.login('editor01')
        resp = self.client.get(reverse('main_app:article_list'),
                               {'category': 'herb', 'status': 'published'})
        qs = resp.context['page_obj'].object_list
        self.assertTrue(all(a.category.code == 'herb' and a.status == 'published' for a in qs))

    def test_normal_user_only_sees_published(self):
        """TC2-9 普通用户只能看到已发布文章"""
        self.login('user01')
        resp = self.client.get(reverse('main_app:article_list'))
        qs = resp.context['page_obj'].object_list
        self.assertTrue(all(a.status == 'published' for a in qs))


# ===========================================================================
# 学生3 咨询问题管理
# ===========================================================================
class Student3ConsultTest(BaseCase):
    """① 咨询记录创建"""

    def test_create_consult_no(self):
        """TC3-1 提交咨询自动生成 ZX+日期+序号 编号"""
        self.login('user01')
        resp = self.client.post(reverse('main_app:consult_create'), {
            'title': '失眠怎么调理', 'consult_type': 'symptom', 'urgency': 1,
            'content': '最近一个月入睡困难，白天乏力，想咨询中医调理方法。',
            'asker_name': '陈小满', 'asker_gender': '女', 'asker_age': 30})
        self.assertEqual(resp.status_code, 302)
        c = Consult.objects.get(title='失眠怎么调理')
        self.assertTrue(c.consult_no.startswith('ZX'))
        self.assertEqual(c.status, 'pending')
        self.assertEqual(c.asker, self.normal)

    def test_content_too_short(self):
        """TC3-2 咨询内容少于 10 字时校验失败"""
        self.login('user01')
        resp = self.client.post(reverse('main_app:consult_create'), {
            'title': '咨询标题', 'consult_type': 'other', 'content': '太短'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Consult.objects.count(), 0)


class Student3DetailTest(BaseCase):
    """② 明细维护"""

    def setUp(self):
        super().setUp()
        self.c = Consult.objects.create(title='黄芪能天天喝吗', consult_type='herb',
                                        content='买了黄芪片每天泡水喝，可以长期喝吗？',
                                        asker=self.normal, asker_name='user01')

    def test_doctor_edit_detail(self):
        """TC3-3 医师修改状态与受理人"""
        self.login('doctor01')
        self.client.post(reverse('main_app:consult_edit', args=[self.c.pk]), {
            'title': self.c.title, 'consult_type': 'herb', 'urgency': 2,
            'status': 'processing', 'handler': self.doctor.pk, 'content': self.c.content})
        self.c.refresh_from_db()
        self.assertEqual(self.c.status, 'processing')
        self.assertEqual(self.c.handler, self.doctor)

    def test_normal_user_cannot_edit(self):
        """TC3-4 普通用户维护明细被拦截（重定向）"""
        self.login('user01')
        resp = self.client.get(reverse('main_app:consult_edit', args=[self.c.pk]))
        self.assertEqual(resp.status_code, 302)


class Student3QueryTest(BaseCase):
    """③ 记录查询与状态查看"""

    def setUp(self):
        super().setUp()
        for i in range(3):
            Consult.objects.create(title=f'咨询{i}', consult_type='symptom',
                                   content='这是测试咨询内容，长度足够。', asker=self.normal,
                                   status='pending' if i == 0 else 'closed')
        self.other = Consult.objects.create(title='他人咨询', consult_type='diet',
                                            content='别人的咨询内容，长度足够。',
                                            asker=self.editor, status='pending')

    def test_user_sees_only_own(self):
        """TC3-5 普通用户列表只包含自己的 3 条"""
        self.login('user01')
        resp = self.client.get(reverse('main_app:consult_list'))
        self.assertEqual(resp.context['page_obj'].paginator.count, 3)

    def test_filter_by_status(self):
        """TC3-6 按状态筛选（待受理）"""
        self.login('doctor01')
        resp = self.client.get(reverse('main_app:consult_list'), {'status': 'pending'})
        self.assertEqual(resp.context['page_obj'].paginator.count, 2)

    def test_claim_consult(self):
        """TC3-7 医师受理后状态变为处理中"""
        self.login('doctor01')
        target = Consult.objects.filter(status='pending').first()
        self.client.post(reverse('main_app:consult_claim', args=[target.pk]))
        target.refresh_from_db()
        self.assertEqual(target.status, 'processing')
        self.assertEqual(target.handler, self.doctor)

    def test_user_cannot_view_others_detail(self):
        """TC3-8 普通用户访问他人咨询被拒绝"""
        self.login('user01')
        resp = self.client.get(reverse('main_app:consult_detail', args=[self.other.pk]))
        self.assertRedirects(resp, reverse('main_app:consult_list'))


# ===========================================================================
# 学生4 回复与审核管理
# ===========================================================================
class Student4ReplyTest(BaseCase):
    """① 回复任务处理"""

    def setUp(self):
        super().setUp()
        self.c = Consult.objects.create(title='秋季干咳食疗', consult_type='diet',
                                        content='秋天干咳无痰，喉咙干痒，有什么食疗方？',
                                        asker=self.normal, status='processing',
                                        handler=self.doctor)

    def test_create_reply_submit(self):
        """TC4-1 医师撰写回复后状态为待审核，并生成 ReviewLog"""
        self.login('doctor01')
        self.client.post(reverse('main_app:reply_create', args=[self.c.pk]), {
            'content': '建议银耳雪梨羹，每日一次，注意避免辛辣食物。'})
        r = Reply.objects.get(consult=self.c)
        self.assertEqual(r.status, 'submitted')
        self.assertTrue(r.reply_no.startswith('HF'))
        self.assertTrue(ReviewLog.objects.filter(reply=r, action='submit').exists())

    def test_exception_requires_note(self):
        """TC4-2 勾选异常备注但未填说明时校验失败"""
        self.login('doctor01')
        resp = self.client.post(reverse('main_app:reply_create', args=[self.c.pk]), {
            'content': '建议线下就诊进一步检查。', 'is_exception': 'on'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Reply.objects.count(), 0)


class Student4ReviewTest(BaseCase):
    """② 审核、确认与状态流转"""

    def setUp(self):
        super().setUp()
        self.c = Consult.objects.create(title='艾灸水泡', consult_type='acupoint',
                                        content='艾灸后起小水泡正常吗？', asker=self.normal,
                                        status='replied', handler=self.doctor)
        self.r = Reply.objects.create(consult=self.c, content='小水泡不要挑破，保持干燥即可。',
                                      replier=self.doctor, status='submitted')

    def test_pass_then_publish(self):
        """TC4-3 审核通过 -> 发布，状态与日志正确"""
        self.login('editor01')
        self.client.post(reverse('main_app:reply_review', args=[self.r.pk]),
                         {'action': 'pass', 'comment': '内容专业'})
        self.r.refresh_from_db()
        self.assertEqual(self.r.status, 'approved')
        self.client.post(reverse('main_app:reply_review', args=[self.r.pk]),
                         {'action': 'publish'})
        self.r.refresh_from_db()
        self.assertEqual(self.r.status, 'published')
        # 初始无 submit 记录，本测试产生 pass + publish 两条
        self.assertEqual(ReviewLog.objects.filter(reply=self.r).count(), 2)

    def test_reject_requires_comment(self):
        """TC4-4 驳回未填意见时失败；填写后咨询退回处理中"""
        self.login('editor01')
        self.client.post(reverse('main_app:reply_review', args=[self.r.pk]), {'action': 'reject'})
        self.r.refresh_from_db()
        self.assertEqual(self.r.status, 'submitted')

        self.client.post(reverse('main_app:reply_review', args=[self.r.pk]),
                         {'action': 'reject', 'comment': '缺少就医提示，请补充'})
        self.r.refresh_from_db()
        self.c.refresh_from_db()
        self.assertEqual(self.r.status, 'rejected')
        self.assertEqual(self.c.status, 'processing')

    def test_publish_requires_approved(self):
        """TC4-5 未经审核直接发布被拒绝"""
        self.login('editor01')
        self.client.post(reverse('main_app:reply_review', args=[self.r.pk]),
                         {'action': 'publish'})
        self.r.refresh_from_db()
        self.assertEqual(self.r.status, 'submitted')

    def test_consultant_cannot_review(self):
        """TC4-6 咨询医师无审核权限（403）"""
        self.login('doctor01')
        resp = self.client.post(reverse('main_app:reply_review', args=[self.r.pk]),
                                {'action': 'pass'})
        self.assertEqual(resp.status_code, 403)


class Student4HistoryTest(BaseCase):
    """③ 异常备注 / 附件 / 历史追踪"""

    def setUp(self):
        super().setUp()
        self.c = Consult.objects.create(title='舌象咨询', consult_type='symptom',
                                        content='舌苔白厚，想咨询调理方法。', asker=self.normal)
        self.r = Reply.objects.create(consult=self.c, content='建议健脾化湿，少食生冷。',
                                      replier=self.doctor, status='submitted',
                                      is_exception=True, exception_note='需结合舌象照片判断')

    def test_history_timeline(self):
        """TC4-7 审核记录按时间倒序展示"""
        ReviewLog.objects.create(reply=self.r, action='submit', operator=self.doctor)
        ReviewLog.objects.create(reply=self.r, action='pass', operator=self.editor,
                                 comment='通过')
        self.login('editor01')
        resp = self.client.get(reverse('main_app:reply_detail', args=[self.r.pk]))
        self.assertEqual(resp.context['reviews'].count(), 2)
        self.assertContains(resp, '需结合舌象照片判断')

    def test_upload_attachment(self):
        """TC4-8 上传附件成功并记录日志"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.login('doctor01')
        f = SimpleUploadedFile('tongue.txt', b'demo file', content_type='text/plain')
        self.client.post(reverse('main_app:reply_detail', args=[self.r.pk]),
                         {'form_type': 'upload', 'file': f})
        self.assertEqual(self.r.attachments.count(), 1)
        self.assertTrue(OperationLog.objects.filter(action='上传附件').exists())


# ===========================================================================
# 学生5 检索统计与日志
# ===========================================================================
class Student5SearchTest(BaseCase):
    """① 多条件查询"""

    def setUp(self):
        super().setUp()
        Article.objects.create(title='黄芪补气全解', category=self.cat, author='李时珍',
                               content='黄芪正文', status='published', created_by=self.editor)
        Consult.objects.create(title='黄芪咨询', consult_type='herb',
                               content='黄芪可以天天喝吗，请解答。', asker=self.normal)

    def test_search_by_keyword(self):
        """TC5-1 关键字联合检索命中文章与咨询"""
        self.login('editor01')
        resp = self.client.get(reverse('main_app:search'), {'kw': '黄芪'})
        self.assertTrue(resp.context['searched'])
        types = {r['type'] for r in resp.context['results']}
        self.assertIn('科普文章', types)
        self.assertIn('咨询问题', types)

    def test_search_by_object_type(self):
        """TC5-2 限定业务对象只返回该类结果"""
        self.login('editor01')
        resp = self.client.get(reverse('main_app:search'), {'obj_type': 'consult'})
        self.assertTrue(all(r['type'] == '咨询问题' for r in resp.context['results']))

    def test_search_by_user(self):
        """TC5-3 按人员过滤"""
        self.login('editor01')
        resp = self.client.get(reverse('main_app:search'), {'user_id': self.editor.pk})
        self.assertTrue(all(r['owner'] == 'editor01' for r in resp.context['results']))

    def test_normal_user_blocked(self):
        """TC5-4 普通用户不能进入综合检索"""
        self.login('user01')
        resp = self.client.get(reverse('main_app:search'))
        self.assertRedirects(resp, reverse('main_app:index'))


class Student5StatTest(BaseCase):
    """② 统计汇总与图表"""

    def setUp(self):
        super().setUp()
        Article.objects.create(title='已发布文章', category=self.cat, author='李',
                               content='内容', status='published', created_by=self.editor)
        Article.objects.create(title='草稿文章', category=self.cat, author='李',
                               content='内容', status='draft', created_by=self.editor)
        Consult.objects.create(title='咨询一', consult_type='symptom',
                               content='这是咨询内容，长度足够。', asker=self.normal)

    def test_dashboard_stat(self):
        """TC5-5 统计卡片数值正确（文章 2 / 已发布 1 / 咨询 1）"""
        self.login('editor01')
        resp = self.client.get(reverse('main_app:stat_dashboard'))
        self.assertEqual(resp.context['stats']['article'], 2)
        self.assertEqual(resp.context['stats']['published'], 1)
        self.assertEqual(resp.context['stats']['consult'], 1)
        self.assertIn('chart_json', resp.context)

    def test_dashboard_chart_json_valid(self):
        """TC5-6 图表 JSON 可解析且趋势数组长度等于天数"""
        import json
        self.login('editor01')
        resp = self.client.get(reverse('main_app:stat_dashboard'), {'days': 7})
        chart = json.loads(resp.context['chart_json'])
        self.assertEqual(len(chart['dates']), 7)
        self.assertEqual(len(chart['article_series']), 7)

    def test_doctor_cannot_view_dashboard(self):
        """TC5-7 咨询医师无统计报表权限"""
        self.login('doctor01')
        self.assertEqual(self.client.get(reverse('main_app:stat_dashboard')).status_code, 403)


class Student5LogTest(BaseCase):
    """③ 日志、导出、打印"""

    def test_log_list_and_filter(self):
        """TC5-8 日志按模块筛选"""
        OperationLog.objects.create(username='editor01', module='article', action='新增文章',
                                    detail='新增科普文章')
        OperationLog.objects.create(username='doctor01', module='reply', action='提交回复',
                                    detail='提交回复')
        self.login('editor01')
        resp = self.client.get(reverse('main_app:log_list'), {'module': 'reply'})
        self.assertEqual(resp.context['page_obj'].paginator.count, 1)

    def test_export_csv(self):
        """TC5-9 导出 CSV 带 BOM、内容含表头"""
        Consult.objects.create(title='导出测试', consult_type='other',
                               content='这是用于导出测试的咨询内容。', asker=self.normal)
        self.login('editor01')
        resp = self.client.get(reverse('main_app:export_csv'), {'target': 'consult'})
        self.assertEqual(resp.status_code, 200)
        self.assertIn('attachment', resp['Content-Disposition'])
        content = resp.content.decode('utf-8')
        self.assertTrue(content.startswith('\ufeff'))
        self.assertIn('咨询编号', content)
        self.assertIn('导出测试', content)

    def test_print_page(self):
        """TC5-10 打印页可渲染"""
        self.login('editor01')
        resp = self.client.get(reverse('main_app:print_view', args=['consult']))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '打印时间')

    def test_auto_log_by_view(self):
        """TC5-11 业务操作自动写日志（新增咨询）"""
        self.login('user01')
        self.client.post(reverse('main_app:consult_create'), {
            'title': '日志验证', 'consult_type': 'other',
            'content': '这是一条用于验证自动留痕的咨询内容。'})
        self.assertTrue(OperationLog.objects.filter(
            username='user01', module='consult', action='新增咨询').exists())


# ===========================================================================
# 端到端闭环：验收场景
# ===========================================================================
class ClosedLoopTest(BaseCase):
    def test_full_business_loop(self):
        """验收：编辑发布文章 -> 用户据此咨询 -> 医师回复 -> 编辑审核发布 -> 日志可追溯"""
        # 1. 编辑发布文章
        self.login('editor01')
        self.client.post(reverse('main_app:article_create'), {
            'title': '足三里日常保健指南', 'category': self.cat.pk, 'author': '李时珍',
            'content': '足三里定位与按揉方法详解。', 'status': 'published',
            'source': '本站原创'})
        art = Article.objects.get(title='足三里日常保健指南')

        # 2. 用户登录并提交咨询（关联文章）
        self.client.logout()
        self.login('user01')
        self.client.post(reverse('main_app:consult_create'), {
            'title': '足三里每天按多久', 'consult_type': 'acupoint',
            'content': '看了文章后开始按足三里，请问每天按多长时间合适？',
            'asker_name': '陈小满', 'related_article': art.pk})
        c = Consult.objects.get(title='足三里每天按多久')
        self.assertEqual(c.related_article, art)

        # 3. 医师受理并回复
        self.client.logout()
        self.login('doctor01')
        self.client.post(reverse('main_app:consult_claim', args=[c.pk]))
        self.client.post(reverse('main_app:reply_create', args=[c.pk]), {
            'content': '建议每侧按揉 3~5 分钟，每日 1~2 次，以酸胀为度。'})
        c.refresh_from_db()
        r = c.replies.first()
        self.assertEqual(c.status, 'replied')

        # 4. 编辑审核通过并发布
        self.client.logout()
        self.login('editor01')
        self.client.post(reverse('main_app:reply_review', args=[r.pk]),
                         {'action': 'pass', 'comment': '专业、有边界提示'})
        self.client.post(reverse('main_app:reply_review', args=[r.pk]), {'action': 'publish'})
        r.refresh_from_db()
        self.assertEqual(r.status, 'published')

        # 5. 全链路日志可追溯
        for mod in ('article', 'consult', 'reply'):
            self.assertTrue(OperationLog.objects.filter(module=mod).exists(),
                            f'{mod} 模块缺少操作日志')
        self.assertEqual(ReviewLog.objects.filter(reply=r).count(), 3)  # submit/pass/publish

        # 6. 用户能看到已发布回复
        self.client.logout()
        self.login('user01')
        resp = self.client.get(reverse('main_app:consult_detail', args=[c.pk]))
        self.assertContains(resp, '每侧按揉 3~5 分钟')
