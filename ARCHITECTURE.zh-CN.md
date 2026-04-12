# 系统架构说明

## 1. 总体架构

```text
Vue 前端  <->  FastAPI 后端  <->  PostgreSQL
                     |
               定时抓取/评分任务
```

- 前端通过 REST API 调用后端。
- 后端负责认证、业务逻辑、数据抓取、社区归属、评分计算。
- PostgreSQL 作为唯一业务数据库。

## 2. 前端结构

- 页面：`frontend/src/pages/*`
- 组件：`frontend/src/components/*`
- API：`frontend/src/services/api.js`
- 状态：`frontend/src/stores/app.js`
- 工具：`frontend/src/utils/*`

核心页面：

- 首页：`Home.vue`
- 事件详情：`EventDetail.vue`
- 社区详情：`CommunityDetail.vue`
- 管理后台：`admin/Dashboard.vue`

## 3. 后端结构

- 入口：`backend/main.py`
- 路由：`backend/routers/*`
- 数据模型：`backend/models.py`
- 请求模型：`backend/schemas.py`
- 安全认证：`backend/security.py`
- 抓取调度：`backend/spider/crawler.py`
- 社区智能归属：`backend/services/community_intelligence.py`
- 评分引擎：`backend/services/scoring.py`

## 4. 数据流程

1. 抓取公开数据源事件。
2. 标准化字段（类型、危险等级、时间、坐标）。
3. 自动归属社区（必要时动态建社区）。
4. 聚类合并动态社区并重命名。
5. 更新社区报告与社区安全评分。
6. 前端实时读取并展示。

## 5. 核心规则

- 地图：离线 GeoJSON 世界底图，默认北美视角。
- 点位：事件点带防重叠分离逻辑。
- 社区评分：分数越高越安全，定时重算。
- 忘记密码：图形验证码 + 邮箱验证码（冷却/有效期约束）。
