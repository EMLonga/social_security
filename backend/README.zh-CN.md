# 后端说明（FastAPI）

## 1. 启动

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

默认地址：`http://127.0.0.1:8000`  
接口文档：`http://127.0.0.1:8000/docs`

## 2. 主要配置

配置文件：`backend/.env`

```env
DATABASE_URL=postgresql+psycopg://postgres:123456@localhost:5432/social_security
JWT_SECRET_KEY=your-secret-key-change-in-production
```

常用变量：

- `CORS_ORIGINS`
- `SOCRATA_APP_TOKEN`
- `SMTP_*`、`EMAIL_DEV_MODE`
- `LLM_API_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`

## 3. 核心模块

- `main.py`：应用入口、路由注册、生命周期任务
- `routers/`：业务路由（auth/events/communities/comments/users/admin/assistant）
- `models.py`：ORM 模型
- `schemas.py`：请求与响应模型
- `security.py`：密码哈希与 JWT
- `spider/crawler.py`：公开数据抓取与调度
- `services/`：社区归属、评分、报告等逻辑

## 4. API 前缀

- 认证：`/api/auth`
- 事件：`/api/events`
- 社区：`/api/communities`
- 用户：`/api/users`
- 管理：`/api/admin`
- 助手：`/api/assistant`

## 5. 任务调度

项目启动时会初始化调度器（APScheduler），用于周期性抓取与相关计算任务；应用关闭时自动停止调度器。
