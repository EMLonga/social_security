# Frontend README（中文）

## 1. 前端简介
前端基于 Vue 3，负责把后端事件与社区数据可视化呈现，包含地图、筛选、分页、详情、报告和后台管理页面。

## 2. 技术栈
- Vue 3
- Vite
- Vue Router
- Pinia
- Element Plus
- Axios
- Leaflet（地图）
- ECharts（图表）

## 3. 目录结构

```text
frontend/
├─ src/
│  ├─ pages/                 # 页面
│  │  ├─ Home.vue
│  │  ├─ EventList.vue
│  │  ├─ EventDetail.vue
│  │  ├─ CommunityList.vue
│  │  ├─ CommunityDetail.vue
│  │  ├─ Auth.vue
│  │  ├─ UserCenter.vue
│  │  └─ admin/Dashboard.vue
│  ├─ components/            # 通用组件（Navbar/Footer/AIAssistant）
│  ├─ services/api.js        # API 适配层
│  ├─ stores/app.js          # Pinia Store
│  ├─ utils/helpers.js       # 工具函数与地名本地化
│  └─ utils/i18n.js          # 文案词典
├─ public/
└─ .env.example
```

## 4. 本地运行

### 4.1 安装依赖
```powershell
cd frontend
npm install
```

### 4.2 配置环境
```powershell
copy .env.example .env
```

### 4.3 启动开发服务
```powershell
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

## 5. 页面功能说明

### 5.1 首页 `Home.vue`
- 地图事件点位展示
- 筛选：事件类型、时间范围
- 热门事件列表（后端 `sortBy=hot`）
- 安全社区排行与统计
- “全部类型”时按类型分别请求并合并排序，降低单一类型挤占

### 5.2 事件列表 `EventList.vue`
- 多条件筛选：关键词、类型多选、社区、时间、风险等级、排序
- 显示总条数
- 分页 + 每页条数切换
- 点赞/收藏快捷操作

### 5.3 事件详情 `EventDetail.vue`
- 事件地图定位
- 详情信息（来源链接、记录 ID、坐标）
- 评论列表与发布/删除
- 点赞、收藏、复制链接、导出文本

### 5.4 社区列表 `CommunityList.vue`
- 社区报告卡片展示
- 分页浏览
- 点击进入社区详情

### 5.5 社区详情 `CommunityDetail.vue`
- 社区评分、等级、趋势
- 人口/面积/30天事件数/主导类型
- 地图：社区中心 + 事件点
- 图表：类型占比饼图、事件趋势折线图
- 报告四要素展示
- 近期事件分页 + 跳转事件详情

### 5.6 认证与个人中心
- `Auth.vue`：登录、注册、找回密码
- `UserCenter.vue`：资料、收藏、关注、我的评论

### 5.7 管理后台
- `admin/Dashboard.vue`：事件/社区/评论/用户/爬虫/敏感词/站点配置管理

## 6. 路由与权限
- 公共：`/`, `/events`, `/events/:id`, `/communities`, `/communities/:id`, `/auth`
- 登录后：`/user`
- 管理员：`/admin`
- 路由守卫在 `src/router.js` 中完成鉴权与角色校验。

## 7. 状态管理

### 7.1 `useUserStore`
- 维护用户信息、token、登录态
- token 同步到 Cookie

### 7.2 `useAppStore`
- 主题（明暗）
- 语言（中英文）

### 7.3 `useFilterStore`
- 全局筛选条件缓存（事件类型、社区、时间范围等）

## 8. API 适配层（重要）
- 文件：`src/services/api.js`
- 职责：
  - 请求拦截器自动带 token
  - 响应拦截器统一处理 401（自动登出）
  - 将 snake_case / camelCase 字段归一化
  - 统一事件/社区/评论结构，减轻页面负担

## 9. 国际化与社区名翻译
- 文案词条：`src/utils/i18n.js`
- 地名翻译：`src/data/city_zh_map.json` + `localizeCommunityName()`
- 中文模式下，社区名会按照州/城市进行本地化展示。

## 10. 地图渲染说明
- 地图基于 Leaflet。
- 使用离散化算法对近距离点位做“分离显示”，减少重叠遮挡。
- 地图底图优先加载 `public/countries.geojson`，失败时有回退渲染。

## 11. 常见问题
- 页面空白：检查后端 `8000` 是否启动，前端是否请求到 `/api`。
- 地图无点：检查事件是否有合法经纬度，且是否被时间/类型筛选排除。
- 中英文切换异常：检查 `localStorage.language` 与翻译词典键值是否一致。
- 分页总数异常：确认后端返回 `total` 与当前筛选参数一致。
