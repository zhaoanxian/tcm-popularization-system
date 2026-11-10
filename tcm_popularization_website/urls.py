"""
项目总路由 —— 中医药科普内容与咨询管理系统
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main_app.urls')),
]

# 开发环境下提供媒体文件（回复附件、文章封面）访问
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / 'static')

admin.site.site_header = '中医药科普内容与咨询管理系统'
admin.site.site_title = '中医药科普管理系统'
admin.site.index_title = '后台数据管理'
