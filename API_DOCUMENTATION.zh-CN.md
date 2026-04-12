# API 文档（简版）

基础地址：`http://localhost:8000/api`  
鉴权方式：`Authorization: Bearer <token>`

## 1. 认证 `/auth`

- `GET /auth/captcha` 获取图形验证码
- `POST /auth/register` 注册
- `POST /auth/login` 登录（用户名或邮箱）
- `POST /auth/password-reset/send-code` 发送邮箱验证码
- `POST /auth/password-reset/confirm` 确认验证码并重置密码
- `GET /auth/me` 当前用户信息

## 2. 事件 `/events`

- `GET /events` 事件列表（支持分页、筛选、排序）
- `GET /events/{event_id}` 事件详情
- `POST /events/{event_id}/like` 点赞
- `DELETE /events/{event_id}/like` 取消点赞
- `POST /events/{event_id}/save` 收藏
- `DELETE /events/{event_id}/save` 取消收藏
- `GET /events/{event_id}/comments` 评论列表
- `POST /events/{event_id}/comments` 发表评论
- `DELETE /events/{event_id}/comments/{comment_id}` 删除评论

## 3. 社区 `/communities`

- `GET /communities` 社区列表
- `GET /communities/{community_id}` 社区详情（含报告）
- `POST /communities/{community_id}/follow` 关注社区
- `DELETE /communities/{community_id}/follow` 取消关注

## 4. 用户 `/users`

- `GET /users/profile`
- `PUT /users/profile`
- `GET /users/saved-events`
- `GET /users/followed-communities`
- `GET /users/comments`

## 5. 管理后台 `/admin`（管理员）

- `GET /admin/dashboard` 概览统计
- `GET /admin/events` / `POST /admin/events` / `PUT /admin/events/{id}` / `DELETE /admin/events/{id}`
- `GET /admin/communities` / `POST /admin/communities` / `PUT /admin/communities/{id}` / `DELETE /admin/communities/{id}`
- `GET /admin/comments` / `DELETE /admin/comments/{id}`
- `POST /admin/comments/{id}/flag` 标记评论
- `POST /admin/comments/{id}/unflag` 取消标记评论
- `PUT /admin/comments/{id}/status` 设置评论标记状态
- `GET /admin/users` / `PUT /admin/users/{id}/role` / `PUT /admin/users/{id}/status` / `DELETE /admin/users/{id}`
- `GET /admin/spider` / `POST /admin/spider/trigger` / `POST /admin/spider/stop`
- `GET /admin/config` / `PUT /admin/config`

完整可交互文档请使用：`http://localhost:8000/docs`
