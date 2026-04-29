# 前端说明（Vue 3）

## 1. 启动

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

默认地址：`http://127.0.0.1:5173`

## 2. 构建

```powershell
npm run build
npm run preview
```

## 3. 关键页面

- `src/pages/Home.vue`：首页地图、热门事件、Top5 社区
- `src/pages/EventDetail.vue`：事件详情、地图、评论互动
- `src/pages/CommunityDetail.vue`：社区详情、图表、报告
- `src/pages/Auth.vue`：登录、注册、找回密码
- `src/pages/admin/Dashboard.vue`：后台管理

## 4. 关键模块

- `src/services/api.js`：接口封装（Axios）
- `src/stores/app.js`：全局状态（Pinia）
- `src/utils/i18n.js`：文案与多语言支持
- `public/countries.geojson`：离线地图边界数据

## 5. 依赖栈

- Vue 3
- Vue Router
- Element Plus
- Pinia
- ECharts
- Leaflet
