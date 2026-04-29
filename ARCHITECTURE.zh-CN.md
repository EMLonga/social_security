# 系统架构说明（Architecture）

## 1. 架构目标
本系统围绕“公开安全事件数据的可用化”设计，核心目标：
- 多源异构数据统一接入
- 自动分类与社区归属
- 可解释的社区安全评分
- 前台可视化 + 后台可运营

## 2. 总体分层

```text
[Data Sources]
  -> [Spider Ingestion]
  -> [Normalization & Classification]
  -> [Community Inference]
  -> [PostgreSQL]
  -> [FastAPI Service Layer]
  -> [Vue Frontend]
```

### 2.1 数据源层
- 城市开放数据（NYC、SF、LA、Chicago、Seattle、Austin 等）
- 自然灾害与预警（USGS、NWS、CAL FIRE、NASA EONET）

### 2.2 采集与清洗层
- 组件：`backend/spider/crawler.py`
- 职责：
  - 拉取各源 JSON
  - 字段提取/时间解析/坐标处理
  - 事件类型判断与风险等级推断
  - 生成更完整的事件叙述（description）
  - 去重入库

### 2.3 业务服务层
- 组件：`backend/services/*`
- 关键能力：
  - 社区归属：`community_intelligence.py`
  - 社区评分：`scoring.py`
  - 报告生成：`build_community_report` / `upsert_community_report`
  - 数据一致性清理：孤儿关系清理、自动社区合并改名

### 2.4 API 层
- 组件：`backend/routers/*`
- 提供认证、事件、社区、评论、用户、管理、助手接口。

### 2.5 前端展示层
- 组件：`frontend/src/pages/*`
- 地图与列表双视图，支持筛选、分页、详情、图表、交互操作。

## 3. 核心领域模型

### 3.1 主要实体
- `User`
- `Event`
- `Community`
- `CommunityReport`
- `Comment`
- `SpiderTask`
- `SensitiveWord`

### 3.2 关键关联
- `Community 1-N Event`
- `Event 1-N Comment`
- `User M-N Event`（点赞、收藏）
- `User M-N Community`（关注）

## 4. 关键流程

### 4.1 采集入库流程
1. 调度器触发抓取任务。
2. 每个数据源执行拉取与字段映射。
3. 归一化为统一事件结构。
4. 基于标题/描述/来源字段推断 `event_type` 和 `danger_level`。
5. 调用社区归属逻辑确定 `community_id`。
6. 去重后写入事件表。
7. 执行社区报告更新和社区评分重算。

### 4.2 社区归属流程（state + city 优先）
1. 从地址提取州和城市候选。
2. 优先精确匹配已有社区（同州同城）。
3. 若无匹配且允许扩展，创建新社区（需通过城市合法性校验）。
4. 若坐标异常或超出美国范围，拒绝归属或走保底逻辑。

### 4.3 社区评分流程
- 输入：社区内所有事件
- 计算项：
  - 时间衰减（越新权重越高）
  - 事件类型权重
  - 风险等级权重
  - 高危/中危/近期/未来预警的结构性惩罚
- 输出：`safety_score`, `safety_level`, `trend`

## 5. 任务调度架构

### 5.1 启动时任务
- 初始化数据库与枚举
- 启动定时任务（若 `SPIDER_ENABLED=true`）
- 立即执行一次评分重算和孤儿清理

### 5.2 周期任务
- 社区评分周期重算
- 数据完整性清理
- 间隔由 `SPIDER_INTERVAL` 控制（最小保护值 300 秒）

## 6. 前端架构

### 6.1 路由
- `/` 首页
- `/events` 事件列表
- `/events/:id` 事件详情
- `/communities` 社区列表
- `/communities/:id` 社区详情
- `/auth` 认证
- `/user` 个人中心（登录）
- `/admin` 后台（管理员）

### 6.2 状态管理
- `useUserStore`：用户、token、登录状态
- `useAppStore`：主题、语言
- `useFilterStore`：全局筛选条件

### 6.3 可视化
- 地图：Leaflet
- 图表：ECharts
- UI：Element Plus

## 7. 国际化与翻译策略
- 文本词条：`frontend/src/utils/i18n.js`
- 地名本地化：`frontend/src/utils/helpers.js` + `city_zh_map.json`
- 社区名翻译仅在展示层进行，后端数据保持英文原始标识。

## 8. 稳定性与一致性设计
- API 参数别名兼容（snake_case / camelCase）
- 列表接口统一分页语义
- 评论显示按可见评论计算（已标记评论不计入展示统计）
- “全部类型”展示做地震占比控制，避免单源主导

## 9. 已知边界
- 地址解析依赖公开数据质量，个别源地址语义不稳定时可能退化到近邻匹配。
- 翻译映射表需持续维护，否则会出现长尾地名未翻译或机器翻译痕迹。

## 10. 可扩展方向
- 引入专用地理编码服务（提升州/城市解析准确率）
- 报告模板细分到事件类型维度
- 热门事件加入时间衰减热度模型
- 增加接口级缓存与查询优化
