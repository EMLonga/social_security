# 社区安全预警平台（中文文档）

本项目是一个前后端分离的社区安全信息平台，提供事件地图展示、社区风险分析、评论互动、用户认证、后台管理与公开数据抓取能力。

## 1. 当前功能范围

- 首页：世界地图、热门事件、Top5 社区
- 事件：列表筛选、详情地图、点赞、收藏、评论
- 社区：社区详情、统计图表、社区报告
- 认证：登录、注册、图形验证码、邮箱找回密码
- 后台：事件/社区/评论/用户管理，抓取任务管理，站点配置
- 数据：公开数据抓取、事件自动归属社区、社区评分自动计算
- AI 助手：基于 OpenAI-compatible 接口的聊天能力

## 2. 技术栈

- 前端：Vue 3 + Vite + Element Plus + Leaflet + ECharts + Pinia
- 后端：FastAPI + SQLAlchemy + APScheduler
- 数据库：PostgreSQL

## 3. 快速启动

### 3.1 一键启动（推荐）

在项目根目录执行：

```powershell
cmd /c start_all.bat
```

默认会启动：

- 前端：`http://127.0.0.1:5173`
- 后端：`http://127.0.0.1:8000`
- API 文档：`http://127.0.0.1:8000/docs`

### 3.2 手动启动

后端：

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

前端：

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

## 4. 关键配置

后端配置文件：`backend/.env`

- `DATABASE_URL`：PostgreSQL 连接串
- `JWT_SECRET_KEY`：JWT 密钥
- `CORS_ORIGINS`：允许跨域来源
- `SOCRATA_APP_TOKEN`：公开数据源令牌（可选）
- `SMTP_*`、`EMAIL_DEV_MODE`：邮件验证码配置
- `LLM_API_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`：AI 助手配置

## 5. 文档索引

- 产品需求：[社区安全预警系统PRD.zh-CN.md](./社区安全预警系统PRD.zh-CN.md)
- 架构说明：[ARCHITECTURE.zh-CN.md](./ARCHITECTURE.zh-CN.md)
- API 文档：[API_DOCUMENTATION.zh-CN.md](./API_DOCUMENTATION.zh-CN.md)
- 后端说明：[backend/README.zh-CN.md](./backend/README.zh-CN.md)
- 前端说明：[frontend/README.zh-CN.md](./frontend/README.zh-CN.md)
- 贡献指南：[CONTRIBUTING.zh-CN.md](./CONTRIBUTING.zh-CN.md)
