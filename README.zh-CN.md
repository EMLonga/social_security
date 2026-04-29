# 社区安全预警系统（Community Safety Alert）

## 1. 项目概述
本项目是一个面向美国公开安全事件的数据聚合与可视化平台，目标是把分散在多个公开数据源中的事件信息统一清洗、分类、归属到社区，并通过地图、列表、社区报告和事件详情页帮助用户快速判断周边风险。

系统由两部分组成：
- 后端：`FastAPI + SQLAlchemy + PostgreSQL`，负责数据采集、清洗、社区归属、评分、报告生成和 API 服务。
- 前端：`Vue 3 + Vite + Element Plus + ECharts + Leaflet`，负责地图展示、筛选检索、详情交互和后台管理界面。

## 2. 核心能力

### 2.1 事件聚合与标准化
- 支持多源公开数据抓取（城市开放数据、USGS 地震、NWS 预警、CAL FIRE、NASA EONET 等）。
- 将不同源字段映射为统一事件模型：`title/description/type/danger_level/time/location/source`。
- 自动去重（按来源记录 ID 或组合键），避免重复入库。

### 2.2 事件分类与风险等级
- 标准事件类型：`theft / shooting / fire / security / fraud / earthquake / other`。
- 风险等级：`low / medium / high`。
- 自动分类逻辑优先使用来源字段语义；无法识别时回落到 `other`。

### 2.3 社区归属（州 + 城市）
- 从地址中解析州和城市，优先命中“同州同城”社区。
- 若无法命中且允许动态扩展，会基于 `state + city + 坐标` 自动创建社区。
- 动态社区命名采用可读格式（例如 `Austin, TX`），避免无意义编号。
- 对无效城市名（坐标串、纯数字、`km of` 噪声）做拦截。

### 2.4 社区评分与趋势
- 定时重算社区安全分（0-100），分数越高越安全。
- 评分考虑：事件类型权重、风险等级权重、时间衰减、近期密度、未来预警。
- 地震事件采用弱化策略（尤其低危地震），避免在统计上“挤压”其他公共安全风险。
- 趋势输出：`up / down / stable`。

### 2.5 社区报告自动生成
- 每个社区自动生成报告字段：
  - 高风险时段
  - 高风险地点
  - 安全建议
  - 近 30 天与前 30 天对比
- 社区列表和社区详情都可读取报告，缺失时自动补生成。

### 2.6 前端地图与筛选
- 首页地图支持按事件类型/时间范围筛选。
- 当“全部类型”时，前端按类型并行拉取数据后合并，减少单类型挤占。
- 事件列表支持多条件筛选：关键词、类型（多选）、社区、时间、风险等级、排序。
- 事件列表和社区列表均支持分页。

### 2.7 热门事件
- “热门事件”由后端 `sort_by=hot` 排序：综合点赞与评论权重，且按发布时间降序打破并列。
- 首页热门模块在当前时间范围内拉取 Top N。

### 2.8 用户与管理
- 用户端：登录注册、找回密码、点赞、收藏、关注社区、评论。
- 管理端：事件/社区/评论/用户管理，敏感词维护，爬虫任务触发与监控，站点配置管理。
- 内置站内 AI 助手接口（可接 OpenAI 兼容 API）。

## 3. 目录结构

```text
social_security/
├─ backend/                      # FastAPI 后端
│  ├─ routers/                   # 路由层
│  ├─ services/                  # 业务服务（归属、评分、报告等）
│  ├─ spider/                    # 多源抓取与调度
│  ├─ models.py                  # 数据模型
│  ├─ schemas.py                 # API 模型
│  ├─ config.py                  # 配置
│  └─ main.py                    # 应用入口
├─ frontend/                     # Vue 前端
│  ├─ src/pages/                 # 页面
│  ├─ src/components/            # 组件
│  ├─ src/services/api.js        # API 封装
│  ├─ src/stores/                # Pinia 状态
│  └─ src/utils/                 # i18n/工具函数
├─ docs/
├─ start_all.bat                 # 一键启动前后端
├─ stop_all.bat                  # 一键停止端口进程
└─ *.zh-CN.md                    # 中文文档
```

## 4. 快速启动

### 4.1 环境要求
- Python 3.10+
- Node.js 18+
- PostgreSQL 14+

### 4.2 后端启动
```powershell
cd backend
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
copy .env.example .env
.\venv\Scripts\python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### 4.3 前端启动
```powershell
cd frontend
npm install
copy .env.example .env
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

### 4.4 Windows 一键启动
```powershell
cmd /c start_all.bat
```

默认访问：
- 前端：`http://127.0.0.1:5173`
- 后端：`http://127.0.0.1:8000`
- 后端 API 文档：`http://127.0.0.1:8000/docs`

## 5. 配置说明（核心）

### 5.1 后端环境变量
见 `backend/.env.example`，重点包括：
- `DATABASE_URL`：数据库连接
- `JWT_SECRET_KEY`：认证密钥
- `CORS_ORIGINS`：跨域白名单
- `SPIDER_ENABLED` / `SPIDER_INTERVAL`：爬虫与周期任务
- `SOCRATA_APP_TOKEN`：Socrata 配额优化
- `SMTP_*`：找回密码邮件
- `LLM_API_*`：站内 AI 助手

### 5.2 前端环境变量
见 `frontend/.env.example`，重点包括：
- `VITE_API_BASE_URL`
- `VITE_DEFAULT_LANGUAGE`
- `VITE_SUPPORTED_LANGUAGES`
- 地图默认中心与缩放级别

## 6. 关键业务规则

### 6.1 “全部类型”展示策略
- 后端在未显式传类型过滤时，会对结果应用地震占比上限（避免列表被单一类型主导）。
- 前端首页地图对“全部类型”采用“按类型分别拉取后合并排序”的方式，提升展示均衡性。

### 6.2 事件总数口径
- 列表返回的 `total` 为数据库过滤后的原始总量，不受当前页展示混合策略影响。

### 6.3 社区命名与翻译
- 社区主命名以英文原始地名为主（州/城市）；中文模式通过映射表与规则翻译展示。
- 翻译层只影响展示，不改变数据库主键与归属逻辑。

## 7. 已实现页面
- 首页（地图、热门事件、安全社区、统计）
- 事件列表（筛选 + 分页）
- 事件详情（地图、来源、评论、点赞收藏导出）
- 社区列表（报告摘要 + 分页）
- 社区详情（地图、图表、报告、近期事件分页）
- 认证页面（登录/注册/找回）
- 个人中心（资料、收藏、关注、评论）
- 管理后台（全局管理）

## 8. 常见问题

### 8.1 为什么有些事件会被归入 `other`？
来源数据字段不完整或语义不稳定时，会先归入 `other`；可通过分类规则补充后重分类。

### 8.2 为什么某些社区事件很多是地震？
地震数据源更新频繁，系统已在“展示层 + 评分层”做抑制（占比与权重）。如需更强控制，可继续调整类型配额和评分权重。

### 8.3 为什么社区数量会增长？
当地址可解析出新的州/城市且允许动态扩展时，系统会自动新建社区承接后续事件，保证归属稳定。

## 9. 相关文档
- `API_DOCUMENTATION.zh-CN.md`
- `ARCHITECTURE.zh-CN.md`
- `backend/README.zh-CN.md`
- `frontend/README.zh-CN.md`
- `社区安全预警系统PRD.zh-CN.md`
