# 前端说明（Vue 3）

## 1. 启动

```powershell
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5174 --strictPort
```

## 2. 构建

```powershell
npm run build
npm run preview
```

## 3. 关键页面

- `src/pages/Home.vue`：首页地图 + 热门事件 + Top5 社区
- `src/pages/EventDetail.vue`：事件详情地图 + 评论互动
- `src/pages/CommunityDetail.vue`：社区地图 + 图表 + 报告
- `src/pages/Auth.vue`：登录/注册/忘记密码
- `src/pages/admin/Dashboard.vue`：后台管理（含分页）

## 4. 地图资源

- 离线世界底图：`public/countries.geojson`
- 点位防重叠逻辑：`Home.vue`、`EventDetail.vue`、`CommunityDetail.vue`

## 5. 接口层

- API 封装：`src/services/api.js`
- 全局状态：`src/stores/app.js`
- 文案与国际化：`src/utils/i18n.js`
