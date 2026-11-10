"""表单定义（校验集中在此，视图只负责流程）。"""
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

from .models import (Article, Attachment, Category, Consult, Reply, Tag,
                     UserProfile)


class RegisterForm(UserCreationForm):
    """学生1 ①：用户注册"""
    real_name = forms.CharField(label='真实姓名', max_length=30, required=True)
    phone = forms.CharField(label='手机号', max_length=20, required=False)
    email = forms.EmailField(label='邮箱', required=False)
    role = forms.ChoiceField(label='注册身份', choices=(
        ('user', '普通用户（提问 / 浏览科普）'),
        ('consultant', '咨询医师（需管理员审核开通）'),
    ), initial='user')

    class Meta:
        model = User
        fields = ('username', 'real_name', 'phone', 'email', 'role', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.setdefault('class', 'form-control')
        self.fields['password1'].widget.attrs['class'] = 'form-control'
        self.fields['password2'].widget.attrs['class'] = 'form-control'
        self.fields['username'].help_text = '登录账号，建议使用拼音或工号'

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.email = self.cleaned_data.get('email', '')
            user.save()
            UserProfile.objects.create(
                user=user,
                role=self.cleaned_data['role'],
                real_name=self.cleaned_data['real_name'],
                phone=self.cleaned_data.get('phone', ''),
            )
        return user


class LoginForm(forms.Form):
    username = forms.CharField(label='账号', widget=forms.TextInput(
        attrs={'class': 'form-control', 'placeholder': '请输入账号'}))
    password = forms.CharField(label='密码', widget=forms.PasswordInput(
        attrs={'class': 'form-control', 'placeholder': '请输入密码'}))


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ('name', 'code', 'description', 'order', 'is_active')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ('name', 'is_active')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ArticleForm(forms.ModelForm):
    """学生2 ①②：新增 / 编辑"""
    class Meta:
        model = Article
        fields = ('title', 'subtitle', 'category', 'tags', 'author', 'source',
                  'summary', 'content', 'cover_image', 'status', 'is_top')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'subtitle': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'tags': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 6}),
            'author': forms.TextInput(attrs={'class': 'form-control'}),
            'source': forms.TextInput(attrs={'class': 'form-control'}),
            'summary': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 12}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'is_top': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_title(self):
        title = self.cleaned_data['title'].strip()
        if len(title) < 4:
            raise forms.ValidationError('标题至少 4 个字，请写清科普主题。')
        return title


class ConsultForm(forms.ModelForm):
    """学生3 ①：提交咨询"""
    class Meta:
        model = Consult
        fields = ('title', 'consult_type', 'urgency', 'content', 'asker_name',
                  'asker_gender', 'asker_age', 'contact', 'related_article')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'consult_type': forms.Select(attrs={'class': 'form-select'}),
            'urgency': forms.Select(attrs={'class': 'form-select'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 6,
                                             'placeholder': '请描述您的具体情况，例如症状、持续时间、既往调理方式……'}),
            'asker_name': forms.TextInput(attrs={'class': 'form-control'}),
            'asker_gender': forms.Select(attrs={'class': 'form-select'}),
            'asker_age': forms.NumberInput(attrs={'class': 'form-control'}),
            'contact': forms.TextInput(attrs={'class': 'form-control'}),
            'related_article': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['related_article'].queryset = Article.objects.filter(status='published')
        self.fields['related_article'].empty_label = '— 不关联 —'
        for name in ('related_article', 'asker_name', 'asker_gender',
                     'asker_age', 'contact'):
            self.fields[name].required = False
        # 有 choices 的整型字段 Django 会当作必填，这里放开并在 clean 中兜底默认值
        self.fields['urgency'].required = False
        self.fields['consult_type'].required = False
        self.fields['urgency'].initial = 1
        self.fields['consult_type'].initial = 'symptom'

    def clean(self):
        data = super().clean() or {}
        data['urgency'] = data.get('urgency') or 1
        data['consult_type'] = data.get('consult_type') or 'symptom'
        return data

    def clean_content(self):
        content = self.cleaned_data['content'].strip()
        if len(content) < 10:
            raise forms.ValidationError('请至少填写 10 个字，方便医师判断。')
        return content


class ConsultAdminForm(forms.ModelForm):
    """学生3 ②③：明细维护（受理人、状态）"""
    class Meta:
        model = Consult
        fields = ('title', 'consult_type', 'urgency', 'status', 'handler',
                  'content', 'asker_name', 'asker_gender', 'asker_age', 'contact',
                  'related_article')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'consult_type': forms.Select(attrs={'class': 'form-select'}),
            'urgency': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'handler': forms.Select(attrs={'class': 'form-select'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'asker_name': forms.TextInput(attrs={'class': 'form-control'}),
            'asker_gender': forms.Select(attrs={'class': 'form-select'}),
            'asker_age': forms.NumberInput(attrs={'class': 'form-control'}),
            'contact': forms.TextInput(attrs={'class': 'form-control'}),
            'related_article': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['handler'].queryset = User.objects.filter(
            profile__role__in=('consultant', 'admin')).order_by('username')
        self.fields['handler'].empty_label = '— 未分配 —'
        for name in ('handler', 'related_article', 'asker_name', 'asker_gender',
                     'asker_age', 'contact', 'urgency', 'status', 'consult_type'):
            self.fields[name].required = False
        self.fields['urgency'].initial = 1
        self.fields['status'].initial = 'pending'

    def clean(self):
        data = super().clean() or {}
        data['urgency'] = data.get('urgency') or (self.instance.urgency or 1)
        data['status'] = data.get('status') or self.instance.status
        data['consult_type'] = data.get('consult_type') or self.instance.consult_type
        return data


class ReplyForm(forms.ModelForm):
    """学生4 ①：回复内容 + 异常备注"""
    class Meta:
        model = Reply
        fields = ('content', 'is_exception', 'exception_note')
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 8,
                                             'placeholder': '请给出专业、通俗、可执行的调理建议，并注明“以上建议不能替代面诊”。'}),
            'is_exception': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'exception_note': forms.TextInput(attrs={'class': 'form-control',
                                                     'placeholder': '如：用户描述不清、疑似需线下就诊、超范围问题'}),
        }

    def clean(self):
        data = super().clean()
        if data.get('is_exception') and not data.get('exception_note'):
            self.add_error('exception_note', '勾选了异常备注，必须填写异常说明。')
        if data.get('content') and len(data['content'].strip()) < 10:
            self.add_error('content', '回复内容至少 10 个字。')
        return data


class AttachmentForm(forms.ModelForm):
    class Meta:
        model = Attachment
        fields = ('file',)
        widgets = {'file': forms.ClearableFileInput(attrs={'class': 'form-control'})}


class ReviewForm(forms.Form):
    """学生4 ②：审核意见"""
    comment = forms.CharField(label='审核意见', required=False, widget=forms.Textarea(
        attrs={'class': 'form-control', 'rows': 2, 'placeholder': '驳回时请说明原因，便于回复人修改'}))
