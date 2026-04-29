# API 文档（中文）

本文档基于当前代码实现（`backend/routers/*.py`）整理，接口前缀默认为 `http://127.0.0.1:8000`。

## 1. 通用约定

### 1.1 鉴权
- 采用 `Bearer Token`（JWT）。
- 需要登录的接口：请求头加 `Authorization: Bearer <token>`。
- 管理接口要求 `admin` 角色。

### 1.2 返回格式
- 列表接口通常返回：
  - `total`: 总条数
  - `events` / `communities` / `comments`: 当前页数据
- 时间字段为 UTC 时间（ISO 字符串）。

### 1.3 分页参数（通用）
- `page`：页码，从 1 开始
- `page_size`：每页条数
- 兼容别名：`pageSize`、`limit`

## 2. 健康检查

### GET `/health`
返回服务状态。

### GET `/`
返回项目名、版本、文档入口。

## 3. 认证模块 `/api/auth`

### GET `/api/auth/captcha`
获取验证码。

### POST `/api/auth/register`
用户注册。

请求体（示例）：
```json
{
  "username": "alice_01",
  "email": "alice@example.com",
  "password": "Pass123456",
  "captcha_id": "...",
  "captcha_answer": "..."
}
```

### POST `/api/auth/login`
用户登录，返回访问令牌。

### POST `/api/auth/password-reset/send-code`
发送重置密码验证码（支持邮件开发模式）。

### POST `/api/auth/password-reset/confirm`
使用验证码完成密码重置。

### GET `/api/auth/me`
获取当前登录用户信息。

## 4. 事件模块 `/api/events`

### 4.1 POST `/api/events`
管理员创建事件，并自动推断社区归属。

### 4.2 GET `/api/events`
事件列表（核心接口）。

#### 查询参数
- `page`, `page_size`
- `event_type`：单类型
- `event_types`：多类型（数组或逗号分隔字符串）
- `community`：社区 ID
- `time_range`：最近 N 天
- `danger_level`：`low|medium|high`
- `sort_by`：`publishTime|hot|likes|comments`
- `search`：关键词（标题/地址/邮编/社区名）

#### 业务规则
- 当未指定类型过滤时，后端会对当前展示集合应用地震占比上限策略（仅影响展示行，不影响 `total`）。
- `sort_by=hot` 使用综合热度排序（点赞权重 + 评论权重），并按时间降序打破并列。

### 4.3 GET `/api/events/{event_id}`
事件详情。

### 4.4 POST `/api/events/{event_id}/like`
点赞事件（需登录）。

### 4.5 DELETE `/api/events/{event_id}/like`
取消点赞（需登录）。

### 4.6 POST `/api/events/{event_id}/save`
收藏事件（需登录）。

### 4.7 DELETE `/api/events/{event_id}/save`
取消收藏（需登录）。

## 5. 评论模块 `/api/events/{event_id}/comments`

### GET `/api/events/{event_id}/comments`
评论列表（支持分页参数）。

### POST `/api/events/{event_id}/comments`
发布评论（需登录，经过敏感词校验）。

### DELETE `/api/events/{event_id}/comments/{comment_id}`
删除评论（仅本人或管理员）。

## 6. 社区模块 `/api/communities`

### 6.1 GET `/api/communities`
社区列表。

#### 查询参数
- 分页：`page`, `page_size`
- `state`, `city`
- `search`
- `sort_by`：`safety_score|created_at|id`
- `sortOrder`：`asc|desc`

#### 返回特性
- 每条社区会携带 `report` 字段。
- 若报告不存在，接口会自动触发生成并返回。

### 6.2 GET `/api/communities/{community_id}`
社区详情，包含：
- 基础信息
- 关注信息（`followers_count`, `is_following`）
- 社区报告
- 事件关联

### 6.3 POST `/api/communities/{community_id}/follow`
关注社区（需登录）。

### 6.4 DELETE `/api/communities/{community_id}/follow`
取消关注（需登录）。

## 7. 用户模块 `/api/users`

### GET `/api/users/profile`
当前用户资料。

### PUT `/api/users/profile`
更新资料。

### GET `/api/users/saved-events`
我的收藏事件。

### GET `/api/users/followed-communities`
我关注的社区。

### GET `/api/users/comments`
我的评论记录。

## 8. 管理模块 `/api/admin`（需管理员）

### 8.1 仪表盘
- `GET /api/admin/dashboard`

### 8.2 事件管理
- `GET /api/admin/events`
- `POST /api/admin/events`
- `PUT /api/admin/events/{event_id}`
- `DELETE /api/admin/events/{event_id}`

### 8.3 社区管理
- `GET /api/admin/communities`
- `POST /api/admin/communities`
- `PUT /api/admin/communities/{community_id}`
- `DELETE /api/admin/communities/{community_id}`

### 8.4 评论管理
- `GET /api/admin/comments`
- `POST /api/admin/comments/{comment_id}/flag`
- `POST /api/admin/comments/{comment_id}/unflag`
- `PUT /api/admin/comments/{comment_id}/status`
- `DELETE /api/admin/comments/{comment_id}`

### 8.5 用户管理
- `GET /api/admin/users`
- `PUT /api/admin/users/{user_id}/role`
- `PUT /api/admin/users/{user_id}/status`
- `DELETE /api/admin/users/{user_id}`

### 8.6 爬虫与任务
- `GET /api/admin/spider`
- `POST /api/admin/spider/trigger`
- `POST /api/admin/spider/stop`
- `POST /api/admin/spider/freeze-core-communities`

### 8.7 站点配置与敏感词
- `GET /api/admin/config`
- `PUT /api/admin/config`
- `POST /api/admin/sensitive-words`
- `DELETE /api/admin/sensitive-words/{word_id}`

## 9. AI 助手模块 `/api/assistant`

### POST `/api/assistant/chat`
输入用户问题 + 页面上下文，返回助手回复。

请求体关键字段：
- `message`
- `language` (`zh`/`en`)
- `page_name`, `page_path`, `page_summary`
- `page_explain`（当前页面解释数组）
- `role`（可选：`guest|user|admin`）

## 10. 常见错误码
- `400`：参数或业务校验失败（如无法根据位置推断社区）
- `401`：未登录或 token 无效
- `403`：权限不足（如访问管理接口）
- `404`：资源不存在
- `422`：请求体字段校验失败
- `502`：外部服务失败（如 AI 接口不可用）

## 11. 联调建议
- 优先通过 `http://127.0.0.1:8000/docs` 验证接口。
- 前端传参建议统一使用：`pageSize`, `timeRange`, `dangerLevel`, `sortBy`，后端已做别名兼容。
- 若出现“有数据但地图无点”，先检查事件是否有合法经纬度与北美范围过滤。
