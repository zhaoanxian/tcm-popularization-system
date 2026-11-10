"""
main_app 路由表 —— 按学生功能包分组
"""
from django.urls import path

from . import views

app_name = 'main_app'

urlpatterns = [
    # ------------------------------ 首页 ------------------------------
    path('', views.index, name='index'),

    # -------------------- 学生1 用户与栏目管理 --------------------
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('user/', views.user_list, name='user_list'),
    path('user/<int:pk>/role/', views.user_role_edit, name='user_role_edit'),
    path('category/', views.category_list, name='category_list'),
    path('category/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('category/<int:pk>/delete/', views.category_delete, name='category_delete'),
    path('tag/', views.tag_list, name='tag_list'),
    path('tag/<int:pk>/delete/', views.tag_delete, name='tag_delete'),
    path('menu/', views.menu_config, name='menu_config'),

    # -------------------- 学生2 科普文章管理 --------------------
    path('article/', views.article_list, name='article_list'),
    path('article/create/', views.article_create, name='article_create'),
    path('article/<int:pk>/', views.article_detail, name='article_detail'),
    path('article/<int:pk>/edit/', views.article_edit, name='article_edit'),
    path('article/<int:pk>/delete/', views.article_delete, name='article_delete'),
    path('article/<int:pk>/toggle/', views.article_toggle_status, name='article_toggle'),

    # -------------------- 学生3 咨询问题管理 --------------------
    path('consult/', views.consult_list, name='consult_list'),
    path('consult/create/', views.consult_create, name='consult_create'),
    path('consult/<int:pk>/', views.consult_detail, name='consult_detail'),
    path('consult/<int:pk>/edit/', views.consult_edit, name='consult_edit'),
    path('consult/<int:pk>/claim/', views.consult_claim, name='consult_claim'),
    path('consult/<int:pk>/close/', views.consult_close, name='consult_close'),

    # -------------------- 学生4 回复与审核管理 --------------------
    path('reply/', views.reply_task_list, name='reply_task_list'),
    path('reply/create/<int:consult_id>/', views.reply_create, name='reply_create'),
    path('reply/<int:pk>/', views.reply_detail, name='reply_detail'),
    path('reply/<int:pk>/review/', views.reply_review, name='reply_review'),

    # -------------------- 学生5 检索统计与日志 --------------------
    path('stat/search/', views.search_view, name='search'),
    path('stat/dashboard/', views.stat_dashboard, name='stat_dashboard'),
    path('stat/log/', views.log_list, name='log_list'),
    path('stat/export/', views.export_csv, name='export_csv'),
    path('stat/print/<str:target>/', views.print_view, name='print_view'),

    # -------------------- 接口 --------------------
    path('api/categories/', views.api_category_options, name='api_categories'),
    path('api/consult/status/', views.api_consult_status, name='api_consult_status'),
]
