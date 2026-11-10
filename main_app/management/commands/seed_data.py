"""
初始化演示数据：python manage.py seed_data
（重复执行会跳过已存在的数据，不会重复插入）
"""
import random
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from main_app.models import (Article, Category, Consult, Menu, OperationLog,
                            Reply, ReviewLog, Tag, UserProfile)

CATEGORIES = [
    ('四季养生', 'health-preserve', '顺应四时调养身心', 1),
    ('中药辨识', 'herb', '常见中药材的功效与鉴别', 2),
    ('穴位保健', 'acupoint', '常用保健穴位与按摩手法', 3),
    ('食疗药膳', 'diet-therapy', '药食同源的日常搭配', 4),
    ('情志调理', 'emotion', '情绪与脏腑的关系', 5),
    ('名医典籍', 'classics', '《黄帝内经》等经典导读', 6),
]

TAGS = ['食疗', '艾灸', '节气', '失眠', '脾胃', '本草', '穴位', '亚健康']

ARTICLES = [
    ('春分养生：疏肝理气，顺应阳气生发', 'health-preserve', '春分时节昼夜平分，人体阳气开始升发，养生重在疏肝理气、调和阴阳。',
     '春分是二十四节气中的第四个节气。此时昼夜平分，寒暑相当，人体阳气开始升发，肝气也随之旺盛。\n\n一、起居：早睡早起，适度舒展肢体，避免久坐。\n\n二、饮食：宜少酸增甘，可适当食用山药、大枣、蜂蜜等，忌过食辛辣与生冷。\n\n三、情志：保持心情舒畅，避免抑郁恼怒伤肝。可饮用玫瑰花茶以疏肝解郁。\n\n四、运动：选择踏青、八段锦等舒缓运动，微微出汗即可，不宜大汗淋漓耗伤阳气。'),
    ('认识黄芪：补气固表的“平民补药”', 'herb', '黄芪味甘性微温，归脾、肺经，为补气要药，适合气虚乏力、易感冒人群。',
     '黄芪为豆科植物蒙古黄芪或膜荚黄芪的干燥根，主产于山西、甘肃、内蒙古等地。\n\n【性味归经】甘，微温。归脾、肺经。\n\n【主要功效】补气升阳、固表止汗、利水消肿、生津养血。\n\n【常见用法】煎服 9~30 克；或与当归配伍成当归补血汤；日常可少量泡水代茶饮。\n\n【注意事项】表实邪盛、阴虚阳亢、疮疡初起者慎用。服用期间如出现口干咽痛、失眠等“上火”表现应减量或停用。\n\n温馨提示：中药需辨证使用，具体用量请咨询执业中医师。'),
    ('足三里：强壮脾胃的“第一保健穴”', 'acupoint', '足三里位于小腿外侧，是足阳明胃经合穴，常按可健脾和胃、扶正培元。',
     '足三里定位：在小腿前外侧，当犊鼻穴下 3 寸，距胫骨前缘一横指（中指）。\n\n【主治】胃痛、腹胀、消化不良、呕吐、泄泻、下肢痿痹，并有强壮保健之效。\n\n【按摩方法】用拇指指腹按揉，力度以酸胀为度，每次 3~5 分钟，每日 1~2 次；亦可艾灸 10~15 分钟。\n\n【适用人群】脾胃虚弱、食欲不振、易疲劳者适合日常保健。\n\n【禁忌】局部皮肤破损、孕妇及高热患者慎用艾灸。'),
    ('秋冬润燥：三款家常食疗方', 'diet-therapy', '秋燥伤肺，银耳雪梨、百合莲子、山药排骨三款食疗方可滋阴润燥、健脾益肺。',
     '秋季燥邪当令，易伤肺阴，出现口干、咽干、皮肤干燥、干咳等症状，饮食宜滋阴润燥。\n\n一、银耳雪梨羹：银耳 15 克泡发，雪梨 1 个切块，加冰糖炖煮 40 分钟，适合干咳少痰者。\n\n二、百合莲子粥：百合 20 克、莲子 30 克、粳米 100 克同煮，适合心烦失眠者。\n\n三、山药排骨汤：山药 200 克、排骨 500 克，文火炖 1 小时，健脾益气，适合体虚乏力者。\n\n【注意】糖尿病患者减少冰糖用量；脾胃虚寒、易腹泻者不宜过量食用银耳与雪梨。'),
    ('情志与五脏：怒伤肝、思伤脾的中医解读', 'emotion', '中医认为五志对应五脏，情绪失调可直接影响脏腑功能，调畅情志是养生重要一环。',
     '《黄帝内经》提出“怒伤肝、喜伤心、思伤脾、忧伤肺、恐伤肾”。\n\n情志过极会扰乱气机：怒则气上，喜则气缓，悲则气消，恐则气下，惊则气乱，思则气结。\n\n日常调摄方法：\n1. 规律作息，避免熬夜耗伤阴血；\n2. 适度运动，如散步、太极、八段锦；\n3. 呼吸吐纳、静坐冥想，帮助气机平顺；\n4. 培养兴趣爱好，及时疏解压力。\n\n若长期情绪低落、失眠、食欲减退，建议及时就诊，必要时结合心理疏导与中药调理。'),
    ('《黄帝内经》四季调神大论导读', 'classics', '“春夏养阳，秋冬养阴”是四时养生的总纲，本篇从起居、饮食、情志三方面阐释顺应自然的养生之道。',
     '《素问·四气调神大论》是中医养生学的纲领性篇章。\n\n【核心观点】“夫四时阴阳者，万物之根本也。所以圣人春夏养阳，秋冬养阴，以从其根。”\n\n【春三月】夜卧早起，广步于庭，被发缓形，以使志生。\n【夏三月】夜卧早起，无厌于日，使志无怒。\n【秋三月】早卧早起，与鸡俱兴，使志安宁。\n【冬三月】早卧晚起，必待日光，使志若伏若匿。\n\n【现代启示】作息与日照节律同步、情绪随季节调整、饮食因地因时制宜，仍是今天可行的养生原则。'),
    ('艾灸入门：常用方法与注意事项', 'acupoint', '艾灸通过温热刺激穴位以温经散寒、扶阳固脱，需掌握距离、时长与禁忌。',
     '常用艾灸方法：温和灸、雀啄灸、回旋灸、隔姜灸。\n\n【操作要点】艾条距皮肤 2~3 厘米，以局部温热、皮肤潮红而不灼痛为度，每穴 10~15 分钟。\n\n【适应】虚寒性胃痛、腹泻、痛经、关节冷痛、阳虚怕冷体质。\n\n【禁忌】高热、阴虚火旺、皮肤破损、出血倾向者禁用；孕妇腰骶部及腹部禁灸；饭后一小时内不宜施灸。\n\n【安全提示】施灸时保持通风，灸后适当饮温水，若出现头晕、心慌（晕灸）应立即停灸并平卧休息。'),
    ('脾胃虚弱怎么调？从三餐做起', 'health-preserve', '脾胃为后天之本，规律三餐、细嚼慢咽、少食生冷是调理脾胃虚弱的第一步。',
     '脾主运化，胃主受纳。脾胃虚弱常见食欲不振、腹胀、便溏、乏力、面色萎黄。\n\n【饮食原则】\n1. 定时定量，早餐不可省；\n2. 食物温热软烂，少食生冷瓜果与冰饮；\n3. 细嚼慢咽，每餐七分饱；\n4. 常食山药、小米、南瓜、红枣、莲子等健脾之品。\n\n【生活调摄】饭后缓行百步，避免立即躺卧；注意腹部保暖；保持情绪舒畅，因“思伤脾”。\n\n【就医提示】若长期腹泻、体重明显下降或便血，应及时到医院完善检查，排除器质性疾病。'),
]

CONSULTS = [
    ('最近总是失眠多梦，白天没精神怎么办？', 'symptom', '最近一个月入睡困难，躺下后要一两个小时才能睡着，夜里容易醒，白天头晕乏力，工作注意力不集中。平时工作压力较大，经常熬夜。想问问中医有什么调理办法？', 2, 0),
    ('黄芪可以天天泡水喝吗？', 'herb', '看到文章说黄芪补气，我买了黄芪片每天泡水喝，已经喝了两周。请问可以长期喝吗？我本身容易上火、口干。', 1, 1),
    ('足三里按压多久合适？', 'acupoint', '按照文章的方法按足三里，按完小腿有点酸胀，请问每天按多久比较合适？酸胀是正常的吗？', 1, 2),
    ('秋天干咳，食疗吃什么好？', 'diet', '一到秋天就干咳，没有痰，喉咙干痒，喝了很多水也不太管用。请问有什么食疗方可以缓解？', 2, 3),
    ('艾灸后皮肤起小水泡正常吗？', 'acupoint', '第一次艾灸足三里，灸完皮肤红红的，第二天起了几个小水泡，有点痒。请问需要处理吗？', 3, 6),
    ('情绪低落、胸闷，中医怎么调理？', 'other', '最近几个月心情一直很低落，胸口发闷，喜欢叹气，吃饭也没胃口，睡眠不好。请问中医有什么办法？', 1, 4),
    ('脾胃虚弱，饭后腹胀怎么办？', 'symptom', '饭后肚子胀得难受，大便不成形，人也没力气。看了脾胃调理的文章，想咨询具体应该怎么吃。', 1, 7),
    ('孕妇可以艾灸吗？', 'acupoint', '怀孕 5 个月，最近腰酸，家人说可以艾灸缓解，请问孕妇能艾灸吗？', 3, 6),
]

REPLY_TEXTS = [
    '您好，从您的描述看，属于中医所说的“心脾两虚、心神失养”证。建议：1）规律作息，尽量 23 点前入睡；2）睡前 1 小时不看手机，可用温水泡脚 15 分钟；3）可尝试按揉神门、内关、三阴交，每穴 2~3 分钟；4）饮食上可用酸枣仁、百合、桂圆煮粥。若两周后仍无改善，建议到中医内科面诊辨证。以上建议不能替代面诊。',
    '您好，黄芪性微温，功在补气固表，但并非人人适合长期服用。您本身容易上火、口干，多属阴虚或内有郁热体质，长期单服黄芪可能加重口干、便秘、失眠等表现。建议暂停，改为辨证配伍使用，如与麦冬、五味子等养阴之品同用，并请中医师面诊后确定用量。',
    '您好，按揉后出现轻度酸胀是正常的“得气”反应，说明刺激到位。建议每次每侧 3~5 分钟，每日 1~2 次，力度以能耐受的酸胀为度，避免用力过猛造成皮下瘀青。饭后半小时内不宜操作。',
    '您好，秋季干咳少痰属燥邪伤肺，可尝试银耳雪梨羹：银耳 15 克泡发、雪梨 1 个切块，加适量冰糖炖 40 分钟，每日一次；也可用百合 20 克、粳米煮粥。避免辛辣、油炸食品。若干咳超过两周或伴发热、痰中带血，请及时就诊。',
    '您好，艾灸后出现小水泡属于轻度烫伤反应，多因距离过近或时间过长。小水泡不要挑破，保持清洁干燥，可自行吸收；若水泡较大或有渗液，应到门诊处理。下次施灸请保持 2~3 厘米距离，每穴不超过 15 分钟。',
    '您好，情志不畅、胸闷叹息、纳差多属肝郁脾虚。建议：1）适度运动，如快走、八段锦，每日 30 分钟；2）可饮用玫瑰花、陈皮代茶饮；3）按揉太冲、期门以疏肝。若情绪低落持续两周以上并影响生活，建议到心理科或中医内科就诊，必要时结合专业心理疏导。',
    '您好，脾胃虚弱者饮食调理建议：1）三餐定时，早餐必吃；2）食物温热软烂，少食生冷；3）每餐七分饱，细嚼慢咽；4）常食山药、小米、南瓜、红枣。可配合按揉足三里。若长期便溏、消瘦，建议完善胃肠检查。',
    '您好，孕妇需慎用艾灸。腰骶部、腹部穴位（如三阴交、合谷、至阴）孕期禁用，以免动胎。孕期腰酸建议通过调整睡姿（侧卧、腿间夹枕）、局部热敷（温度不宜过高）缓解，必要时请产科或中医妇科面诊。',
]

MENUS = [
    ('科普文章', 'article_manage', 'main_app:article_list', 'bi-journal-text', 'admin,editor,consultant,user', 1),
    ('咨询问题', 'consult_manage', 'main_app:consult_list', 'bi-chat-square-text', 'admin,editor,consultant,user', 2),
    ('回复审核', 'reply_manage', 'main_app:reply_task_list', 'bi-check2-square', 'admin,editor,consultant', 3),
    ('综合检索', 'stat_search', 'main_app:search', 'bi-search', 'admin,editor,consultant', 4),
    ('统计报表', 'stat_report', 'main_app:stat_dashboard', 'bi-bar-chart', 'admin,editor', 5),
    ('操作日志', 'stat_log', 'main_app:log_list', 'bi-list-check', 'admin,editor', 6),
    ('用户管理', 'user_manage', 'main_app:user_list', 'bi-people', 'admin', 7),
    ('栏目管理', 'category_manage', 'main_app:category_list', 'bi-folder2-open', 'admin', 8),
    ('权限配置', 'menu_config', 'main_app:menu_config', 'bi-shield-lock', 'admin', 9),
]

USERS = [
    ('admin01', 'admin', '系统管理员', '13800000001', '信息科'),
    ('editor01', 'editor', '李时珍', '13800000002', '科普编辑部'),
    ('editor02', 'editor', '张景岳', '13800000003', '科普编辑部'),
    ('doctor01', 'consultant', '王清任', '13800000004', '中医内科'),
    ('doctor02', 'consultant', '叶天士', '13800000005', '针灸科'),
    ('user01', 'user', '陈小满', '13900000001', ''),
    ('user02', 'user', '刘一诺', '13900000002', ''),
    ('user03', 'user', '赵子期', '13900000003', ''),
]

PASSWORD = 'tcm123456'


class Command(BaseCommand):
    help = '初始化中医药科普系统的演示数据（用户 / 栏目 / 标签 / 文章 / 咨询 / 回复 / 日志）'

    def handle(self, *args, **options):
        random.seed(20250101)
        now = timezone.now()

        # ---------------- 菜单权限 ----------------
        for name, code, url_name, icon, roles, order in MENUS:
            Menu.objects.update_or_create(
                code=code,
                defaults=dict(name=name, url_name=url_name, icon=icon,
                              roles=roles, order=order, is_active=True))

        # ---------------- 用户 ----------------
        users = {}
        for username, role, real_name, phone, dept in USERS:
            u, created = User.objects.get_or_create(username=username, defaults={
                'email': f'{username}@tcm.edu.cn', 'is_staff': role == 'admin'})
            u.is_staff = role == 'admin'
            u.is_superuser = username == 'admin01'
            u.set_password(PASSWORD)
            u.save()
            UserProfile.objects.update_or_create(user=u, defaults={
                'role': role, 'real_name': real_name, 'phone': phone,
                'department': dept, 'is_active_account': True})
            users[username] = u
        self.stdout.write(f'  用户 {len(users)} 个（密码统一 {PASSWORD}）')

        # ---------------- 栏目 / 标签 ----------------
        cats = {}
        for name, code, desc, order in CATEGORIES:
            c, _ = Category.objects.get_or_create(code=code, defaults={
                'name': name, 'description': desc, 'order': order})
            cats[code] = c
        tag_objs = [Tag.objects.get_or_create(name=t)[0] for t in TAGS]

        # ---------------- 文章 ----------------
        editors = [users['editor01'], users['editor02'], users['admin01']]
        arts = []
        for i, (title, cat, summary, content) in enumerate(ARTICLES):
            a, _ = Article.objects.get_or_create(title=title, defaults=dict(
                category=cats[cat], author=editors[i % 3].profile.real_name,
                source='本站原创', summary=summary, content=content,
                status='published', is_top=(i == 0),
                created_by=editors[i % 3],
                published_at=now - timedelta(days=random.randint(1, 20)),
            ))
            if a.tags.count() == 0:
                a.tags.set(random.sample(tag_objs, k=2))
            # auto_now_add=True 会在 save() 时覆盖手工赋值，故用 update() 写回
            Article.objects.filter(pk=a.pk).update(
                created_at=now - timedelta(days=random.randint(1, 25),
                                           hours=random.randint(0, 20)))
            arts.append(a)

        # 额外填充几篇草稿，便于测试分页与筛选
        draft_days = [2, 4, 7, 11, 15, 19]
        for i, days_ago in enumerate(draft_days, start=1):
            title = f'中医体质辨识系列（{i}）：{["平和质", "气虚质", "阳虚质", "阴虚质", "痰湿质", "血瘀质"][i-1]}的辨识与调养'
            d, _ = Article.objects.get_or_create(title=title, defaults=dict(
                category=cats['health-preserve'], author='张景岳',
                summary='九种体质辨识要点与日常调养建议。', content='内容待完善……',
                status='draft', created_by=users['editor02']))
            Article.objects.filter(pk=d.pk).update(
                created_at=now - timedelta(days=days_ago, hours=random.randint(1, 9)))
        self.stdout.write(f'  科普文章 {Article.objects.count()} 篇')

        # ---------------- 咨询 ----------------
        askers = [users['user01'], users['user02'], users['user03']]
        doctors = [users['doctor01'], users['doctor02']]
        created_consults = []
        for i, (title, ctype, content, urgency, art_idx) in enumerate(CONSULTS):
            asker = askers[i % 3]
            c, _ = Consult.objects.get_or_create(title=title, defaults=dict(
                consult_type=ctype, content=content, urgency=urgency,
                asker=asker, asker_name=asker.profile.real_name,
                asker_gender='女' if i % 2 else '男',
                asker_age=random.randint(22, 58),
                contact='139****' + str(1000 + i),
                related_article=arts[art_idx] if art_idx < len(arts) else None,
                status='pending',
            ))
            day_off = len(CONSULTS) * 2 - i * 2
            Consult.objects.filter(pk=c.pk).update(
                created_at=now - timedelta(days=day_off, hours=random.randint(0, 12)))
            c.refresh_from_db()
            created_consults.append(c)

        # ---------------- 回复 + 审核 ----------------
        status_plan = ['published', 'published', 'approved', 'submitted',
                       'rejected', 'published', 'submitted', 'draft']
        for i, c in enumerate(created_consults):
            if Reply.objects.filter(consult=c).exists():
                continue
            target = status_plan[i]
            doctor = doctors[i % 2]
            r = Reply.objects.create(
                consult=c, content=REPLY_TEXTS[i], replier=doctor,
                status=target,
                is_exception=(i == 4),
                exception_note='艾灸后出现水泡，建议线下查看创面' if i == 4 else '')
            r_time = c.created_at + timedelta(hours=6)
            Reply.objects.filter(pk=r.pk).update(created_at=r_time)
            r.refresh_from_db()
            ReviewLog.objects.create(reply=r, action='submit', operator=doctor,
                                     comment='提交审核')
            if target in ('approved', 'published', 'rejected'):
                ReviewLog.objects.create(
                    reply=r,
                    action='pass' if target != 'rejected' else 'reject',
                    operator=users['editor01'],
                    comment='内容专业，建议补充就医提示' if target != 'rejected' else '回复中缺少“不能替代面诊”的提示，请补充后重新提交。')
            if target == 'published':
                ReviewLog.objects.create(reply=r, action='publish', operator=users['editor01'],
                                         comment='发布给用户')
                c.status = 'replied' if i != len(created_consults) - 1 else 'closed'
            elif target == 'approved':
                c.status = 'replied'
            elif target == 'submitted':
                c.status = 'replied'
            else:
                c.status = 'processing'
            c.handler = doctor
            c.save()

        # 统一修正审核记录时间（auto_now_add 会覆盖）
        for rv in ReviewLog.objects.select_related('reply').all():
            delta = {'submit': timedelta(minutes=5),
                     'pass': timedelta(hours=3),
                     'reject': timedelta(hours=3),
                     'publish': timedelta(hours=4)}.get(rv.action, timedelta(hours=5))
            ReviewLog.objects.filter(pk=rv.pk).update(
                created_at=rv.reply.created_at + delta)

        # 让第一条已发布咨询走完整闭环（结案）
        first = created_consults[0]
        first_reply = Reply.objects.filter(consult=first).first()
        if first_reply:
            first_reply.status = 'published'
            first_reply.save()
            ReviewLog.objects.get_or_create(reply=first_reply, action='close',
                                            defaults={'operator': users['doctor01'],
                                                      'comment': '用户已确认，结案'})
            first.status = 'closed'
            first.save()
        self.stdout.write(f'  咨询 {Consult.objects.count()} 条 / 回复 {Reply.objects.count()} 条')

        # ---------------- 操作日志 ----------------
        if OperationLog.objects.count() < 20:
            logs = [
                ('admin01', 'auth', '登录', 'User', '管理员登录系统'),
                ('editor01', 'article', '新增文章', 'Article', '新增科普文章：春分养生：疏肝理气，顺应阳气生发'),
                ('editor01', 'article', '编辑文章', 'Article', '编辑科普文章：认识黄芪：补气固表的“平民补药”'),
                ('editor02', 'article', '新增文章', 'Article', '新增草稿：中医体质辨识系列（1）'),
                ('doctor01', 'consult', '受理咨询', 'Consult', '受理 ZX 开头的咨询记录'),
                ('doctor01', 'reply', '提交回复', 'Reply', '提交回复并进入待审核'),
                ('editor01', 'reply', '审核通过', 'Reply', '回复审核通过'),
                ('editor01', 'reply', '发布回复', 'Reply', '回复发布给用户'),
                ('editor01', 'reply', '审核驳回', 'Reply', '驳回：缺少就医提示'),
                ('admin01', 'category', '新增栏目', 'Category', '新增栏目：食疗药膳'),
                ('admin01', 'user', '角色调整', 'UserProfile', 'user02: 普通用户 -> 咨询医师'),
                ('editor01', 'stat', '导出数据', 'Export', '导出 consult 数据'),
                ('editor01', 'stat', '综合检索', 'Query', '条件 kw=黄芪，命中 6 条'),
                ('user01', 'auth', '登录', 'User', '普通用户登录'),
                ('user01', 'consult', '新增咨询', 'Consult', '提交咨询：最近总是失眠多梦'),
                ('doctor02', 'reply', '上传附件', 'Reply', '上传舌象照片'),
                ('editor01', 'article', '状态变更', 'Article', '文章下架'),
                ('admin01', 'user', '菜单权限配置', 'Menu', '统计报表 可见角色 -> admin,editor'),
                ('user02', 'auth', '登录失败', 'User', '账号或密码错误'),
                ('editor01', 'stat', '导出数据', 'Export', '导出 article 数据'),
            ]
            for i, (uname, module, action, otype, detail) in enumerate(logs):
                u = User.objects.filter(username=uname).first()
                log = OperationLog.objects.create(
                    user=u, username=uname, module=module, action=action,
                    object_type=otype, detail=detail, ip='127.0.0.1',
                    result='fail' if '失败' in action else 'success')
                OperationLog.objects.filter(pk=log.pk).update(
                    created_at=now - timedelta(days=random.randint(0, 13),
                                               hours=random.randint(0, 23)))
        self.stdout.write(f'  操作日志 {OperationLog.objects.count()} 条')

        self.stdout.write(self.style.SUCCESS('\n演示数据初始化完成！'))
        self.stdout.write('  管理员：admin01 / %s' % PASSWORD)
        self.stdout.write('  编辑  ：editor01 / %s' % PASSWORD)
        self.stdout.write('  医师  ：doctor01 / %s' % PASSWORD)
        self.stdout.write('  用户  ：user01 / %s' % PASSWORD)
