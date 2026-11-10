# 中医药科普内容与咨询管理系统

> 基于 Python + Django 的中医药科普内容与咨询管理系统（课程设计 / 教学实践项目）
>
> 业务闭环：**科普文章管理 → 咨询问题管理 → 回复与审核管理 → 检索统计与日志**

一个面向普通用户的中医药科普平台：用户浏览科普文章、就文章内容向医师提问，医师撰写回复，编辑审核后发布，全程留痕并可统计导出。

---

## 功能模块

| 模块 | 主要功能 | 关键设计 |
|---|---|---|
| **用户与栏目** | 注册登录、角色分配、栏目与标签管理、菜单权限配置 | 角色校验 + 菜单开关两层权限 |
| **科普文章** | 文章增删改查、封面上传、标签、置顶、草稿/发布/下架 | 三态替代布尔；多对多筛选去重 |
| **咨询问题** | 用户提交咨询、自动编号、医师受理、状态流转 | `ZX+日期+序号`；越权访问拦截 |
| **回复与审核** | 撰写回复、异常备注、提交审核、审核通过、发布、历史追踪 | 状态机 + 审核日志；审核与发布分离 |
| **检索统计与日志** | 跨表检索、统计看板、趋势图、操作日志、CSV 导出 | 分组补零；UTF-8 BOM 导出 |

---

## 角色与权限

| 角色 | 能做什么 |
|---|---|
| 系统管理员 | 全部功能，包括用户、栏目、菜单权限 |
| 科普编辑 | 文章维护、回复审核与发布、统计报表 |
| 咨询医师 | 受理咨询、撰写并提交回复 |
| 普通用户 | 浏览科普、提交咨询、查看自己的回复 |

权限分两层实现：

- `@role_required` —— 校验当前用户角色，不匹配直接返回 **403**
- `@module_required` —— 查 `Menu` 表中该角色是否开启对应菜单，未开启则 **302** 重定向回首页

> 代码层拦住"身份不对"，数据库层控制"功能开关"，两者互补。

---

## 技术栈

- Python 3.10+ / Django 4.x
- SQLite（默认，开箱即用）；设置 `DB_ENGINE=mysql` 可切换 MySQL
- Pandas —— 统计分组与聚合
- ECharts 5 —— 前端图表（CDN 引入）
- 原生 HTML / CSS / JavaScript，无前端框架

---

## 快速开始

```bash
# 1. 克隆
git clone https://github.com/zhaoanxian/tcm-popularization-system.git
cd tcm-popularization-system

# 2. 建虚拟环境
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 3. 装依赖
pip install -r requirements.txt

# 4. 建表（仓库已带 db.sqlite3，此步会提示 No migrations to apply，属正常）
python manage.py migrate

# 5. 启动
python manage.py runserver
```

浏览器打开 <http://127.0.0.1:8000/>

> 仓库中已包含带演示数据的 `db.sqlite3`，克隆后可直接运行。
> 如需从空库重建演示数据，删除 `db.sqlite3` 后执行 `migrate` + `python manage.py seed_data`。

### 演示账号（密码统一 `tcm123456`）

| 账号 | 角色 |
|---|---|
| `admin01` | 系统管理员 |
| `editor01` / `editor02` | 科普编辑 |
| `doctor01` / `doctor02` | 咨询医师 |
| `user01` / `user02` / `user03` | 普通用户 |

后台管理：<http://127.0.0.1:8000/admin/>

---

## 项目结构

```
tcm-popularization-system/
├── manage.py
├── requirements.txt
├── db.sqlite3                    # 含演示数据的 SQLite 数据库
├── tcm_popularization_website/   # 项目配置
│   ├── settings.py               # 数据库、媒体、中间件、本地化
│   └── urls.py
├── main_app/                     # 主应用
│   ├── models.py                 # 10 个模型：栏目/标签/文章/咨询/回复/审核日志…
│   ├── views.py                  # 40+ 视图，按学生分工注释
│   ├── forms.py                  # 表单校验
│   ├── permissions.py            # 两个权限装饰器
│   ├── middleware.py             # 操作日志中间件
│   ├── context_processors.py     # 菜单按角色渲染
│   ├── tests.py                  # 48 个单元测试
│   └── management/commands/seed_data.py
├── templates/                    # 页面模板
└── static/css/style.css
```

---

## 数据模型

| 模型 | 说明 |
|---|---|
| `Category` / `Tag` | 科普栏目、文章标签 |
| `Article` | 科普文章，状态：草稿 / 已发布 / 已下架 |
| `Consult` | 咨询问题，状态：待受理 / 处理中 / 已回复 / 已关闭 |
| `Reply` | 回复，状态：草稿 / 待审核 / 已通过 / 已发布 / 已驳回 |
| `ReviewLog` | 审核流转记录（谁、何时、做了什么） |
| `Attachment` | 回复附件 |
| `OperationLog` | 操作日志（模块、动作、IP、结果） |
| `UserProfile` | 用户角色扩展 |
| `Menu` | 菜单与接口权限矩阵 |

---

## 测试

```bash
python manage.py test main_app -v 2
```

覆盖注册登录、角色权限、栏目增删、文章状态、咨询流转、回复审核、检索统计与导出等场景，共 **48 个用例**，全部通过。

---

## 说明

本项目为课程设计作品，用于教学演示。演示数据中的文章内容仅作功能展示，不构成任何医疗建议。
