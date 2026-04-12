# 后端说明（FastAPI）

## 1. 启动

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

默认监听：`http://127.0.0.1:8000`

## 2. 数据库

当前默认使用 PostgreSQL，请在 `backend/.env` 配置：

```env
DATABASE_URL=postgresql+psycopg://postgres:123456@localhost:5432/social_security
```

## 3. 核心模块

- `routers/`：业务路由（auth/events/communities/comments/users/admin）
- `models.py`：ORM 模型
- `schemas.py`：请求与响应结构
- `security.py`：密码哈希与 JWT
- `spider/crawler.py`：公开数据抓取与调度
- `services/community_intelligence.py`：社区归属/合并/报告
- `services/scoring.py`：社区评分

## 4. 抓取与任务

- 支持公开数据源抓取（含实时与城市源）。
- 抓取后会触发社区合并、重命名、报告更新、评分重算。
- 定时任务由 APScheduler 驱动。

## 5. 邮件与 AI 助手

- 邮件验证码相关配置：`SMTP_*`、`EMAIL_DEV_MODE`
- AI 助手配置：`LLM_API_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`
