# Backend README（中文）

## 1. 后端简介
后端基于 FastAPI，负责：
- 多源事件采集与入库
- 事件分类与风险分级
- 社区归属（州+城市）
- 社区评分与报告生成
- 用户、评论、管理后台 API
- 站内 AI 助手对话接口

## 2. 目录结构

```text
backend/
├─ routers/                  # API 路由
├─ services/                 # 业务服务
├─ spider/                   # 抓取与调度
├─ config.py                 # 配置
├─ database.py               # DB 引擎与会话
├─ models.py                 # ORM 模型
├─ schemas.py                # 请求/响应模型
├─ security.py               # JWT 与权限
├─ main.py                   # 应用入口
└─ .env.example              # 环境变量模板
```

## 3. 技术栈
- FastAPI
- SQLAlchemy 2.x
- PostgreSQL（`psycopg`）
- APScheduler
- aiohttp（抓取）

## 4. 本地启动

### 4.1 安装依赖
```powershell
cd backend
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
```

### 4.2 配置环境变量
```powershell
copy .env.example .env
```

最少要改：
- `DATABASE_URL`
- `JWT_SECRET_KEY`

### 4.3 启动服务
```powershell
.\venv\Scripts\python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

访问：
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

## 5. 关键配置

### 5.1 数据库
- 由 `DATABASE_URL` 控制。
- `init_db()` 启动时自动建表。
- PostgreSQL 下会尝试同步新增枚举值（如 `EARTHQUAKE`）。

### 5.2 爬虫与调度
- `SPIDER_ENABLED=true/false`
- `SPIDER_INTERVAL`（秒）
- 启动时会执行一次评分重算和数据完整性清理。

### 5.3 认证
- JWT 算法：`HS256`
- 默认过期：`ACCESS_TOKEN_EXPIRE_MINUTES=1440`

### 5.4 邮件找回密码
- `SMTP_*` 全套配置
- `EMAIL_DEV_MODE=true` 可用于本地调试

### 5.5 AI 助手
- `LLM_API_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`
- `LLM_TIMEOUT_SECONDS`

## 6. API 模块说明
- `auth.py`：注册、登录、验证码、找回密码、当前用户
- `events.py`：事件列表/详情、点赞收藏、管理员创建
- `comments.py`：评论增删查
- `communities.py`：社区列表/详情、关注
- `users.py`：个人资料、收藏、关注、评论
- `admin.py`：后台全量管理能力
- `assistant.py`：AI 聊天接口

## 7. 社区归属与社区管理

### 7.1 归属逻辑
- 优先按地址提取 `state + city` 做精确匹配。
- 匹配失败可创建动态社区（需合法性校验）。
- 对明显无效城市 token（含坐标串、纯数字、无效结构）会拒绝创建。

### 7.2 社区模板
- 支持从 `core_communities.generated.json` 读取模板。
- `ensure_core_communities()` 仅在社区表为空时初始化，避免重复膨胀。

### 7.3 自动治理
- 支持自动社区合并（Auto Zone）
- 支持自动重命名，提高社区可读性
- 支持孤儿关系清理

## 8. 评分与报告

### 8.1 社区评分
- 文件：`services/scoring.py`
- 计算维度：类型权重、风险权重、时间衰减、近期与未来事件惩罚
- 地震低危影响会被弱化

### 8.2 社区报告
- 文件：`services/community_intelligence.py`
- 输出：高风险时段、高风险地点、安全建议、近 30 天对比
- 缺失报告会在读取社区接口时自动补写

## 9. 抓取系统

### 9.1 数据源
- 城市开放治安数据（NYC/SF/LA/Chicago/Seattle/Austin）
- USGS 地震
- NWS 预警
- CAL FIRE
- NASA EONET
- OpenDataPhilly
- DC MPD

### 9.2 运行方式
- 管理接口手动触发：`POST /api/admin/spider/trigger`
- 或由调度器按 `SPIDER_INTERVAL` 周期执行评分与清理任务

## 10. 初始化脚本
- `init_data.py`：用于快速生成测试数据（会清空部分表数据，谨慎在生产库使用）。

## 11. 排错建议
- 无法连接数据库：检查 `DATABASE_URL` 与 PostgreSQL 服务。
- 401 大量出现：检查前端 token 是否过期并确认时钟正常。
- 社区数量异常增长：检查地址解析质量与动态创建策略。
- 地震事件占比过高：检查抓取源数据结构与前端筛选策略。
