# 社区安全预警平台（中文文档）

本项目是一个前后端分离的社区安全信息平台，提供事件地图展示、社区风险分析、评论互动、用户认证、后台管理与公开数据抓取能力。

## 1. 当前功能范围

- 首页：世界地图底图（默认聚焦北美）、热点事件、Top5 社区。
- 事件：列表筛选、详情地图、点赞、收藏、评论、分享与导出。
- 社区：社区地图、图表、自动生成的社区报告。
- 认证：登录/注册图形验证码、忘记密码邮箱验证码（30 秒冷却，5 分钟有效）。
- 后台：事件/社区/评论/用户管理，评论标记与取消标记，抓取任务管理，站点配置。
- 数据：公开数据源抓取、事件自动归属社区、社区自动评分与定时重算。

## 2. 技术栈

- 前端：Vue 3 + Vite + Element Plus + Leaflet + ECharts + Pinia
- 后端：FastAPI + SQLAlchemy + APScheduler
- 数据库：PostgreSQL（当前默认）

## 3. 快速启动

### 3.1 一键启动（推荐）

在项目根目录执行：

```powershell
cmd /c start_all.bat
```

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
npm run dev -- --host 0.0.0.0 --port 5174 --strictPort
```

访问地址：

- 前端：`http://localhost:5174`
- 后端：`http://localhost:8000`
- API 文档：`http://localhost:8000/docs`

## 4. 关键配置

后端配置文件：`backend/.env`

- `DATABASE_URL`：PostgreSQL 连接串
- `JWT_SECRET_KEY`：JWT 密钥
- `SOCRATA_APP_TOKEN`：城市公开数据源令牌（可选但建议配置）
- `SMTP_*`、`EMAIL_DEV_MODE`：邮件验证码配置
- `LLM_*`：AI 助手大模型配置（支持 OpenAI-compatible）

## 5. 机制说明（当前版本）

- 事件归属：按经纬度/地址自动推断社区；远距离事件自动创建核心社区并可聚类合并。
- 地图点位：带防重叠分离逻辑，减少密集点遮挡。
- 社区评分：由社区全部事件自动计算，分数越高表示越安全，并通过定时任务重算。

## 6. 文档索引

- 产品需求：[社区安全预警系统PRD.zh-CN.md](./社区安全预警系统PRD.zh-CN.md)
- 架构设计：[ARCHITECTURE.zh-CN.md](./ARCHITECTURE.zh-CN.md)
- API 文档：[API_DOCUMENTATION.zh-CN.md](./API_DOCUMENTATION.zh-CN.md)
- 后端说明：[backend/README.zh-CN.md](./backend/README.zh-CN.md)
- 前端说明：[frontend/README.zh-CN.md](./frontend/README.zh-CN.md)
- 贡献指南：[CONTRIBUTING.zh-CN.md](./CONTRIBUTING.zh-CN.md)
