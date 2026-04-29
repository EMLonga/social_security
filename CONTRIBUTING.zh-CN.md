# 贡献指南（Contributing）

欢迎参与本项目。本文档用于统一开发流程、代码风格和提交规范，减少协作摩擦。

## 1. 分支与提交流程

### 1.1 分支策略
- `main`：稳定分支。
- 功能开发请使用：`feature/<name>`。
- 缺陷修复请使用：`fix/<name>`。
- 文档更新请使用：`docs/<name>`。

### 1.2 提交建议
提交信息尽量包含“模块 + 动作 + 影响”，例如：
- `backend(events): fix mixed type filtering when event_types provided`
- `frontend(community): add pagination for report list`
- `docs(api): update admin spider endpoints`

### 1.3 PR 要求
PR 描述至少包含：
- 背景与目标
- 改动范围（文件/模块）
- 验证方式（接口、页面、截图）
- 风险点与回滚方案（如涉及数据脚本）

## 2. 本地开发环境

### 2.1 后端
```powershell
cd backend
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
copy .env.example .env
.\venv\Scripts\python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### 2.2 前端
```powershell
cd frontend
npm install
copy .env.example .env
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

### 2.3 一键启动
```powershell
cmd /c start_all.bat
```

## 3. 代码规范

### 3.1 Python（后端）
- 路由层只处理协议与参数，复杂逻辑放 `services/`。
- 数据库会话必须使用依赖注入或显式关闭。
- 新增枚举值时，注意数据库 enum 同步。
- 返回结构要与 `schemas.py` 对齐。

### 3.2 Vue/JS（前端）
- 页面逻辑在 `pages/`，复用逻辑放 `utils/` / `services/`。
- API 字段统一走 `services/api.js` 归一化，不在页面重复转换。
- 所有分页接口必须保留 `total` 显示。
- 国际化文本优先使用 `i18n`，避免硬编码。

### 3.3 文档
- 文档以 UTF-8 保存。
- 描述必须与实际代码行为一致，不写“未来可能”作为当前能力。

## 4. 关键开发约束

### 4.1 社区归属
- 以“州 + 城市”作为主要归属维度。
- 动态社区创建必须经过合法性校验，避免垃圾社区名。

### 4.2 事件分类
- 优先识别 `earthquake`，其余类型按规则映射。
- 不确定分类进入 `other`，并在后续规则迭代中回填。

### 4.3 展示一致性
- 列表展示条数与 `total` 的语义必须清晰区分。
- 热门事件排序规则必须前后端一致。

## 5. 测试与验收清单
提交前建议至少完成：

### 5.1 后端
- 事件列表筛选：类型、社区、时间、风险、搜索、排序
- 社区列表分页与排序
- 热门排序返回正确
- 登录态接口 401/403 行为正确

### 5.2 前端
- 首页地图在中英文下展示正常
- 事件列表筛选与分页正确
- 社区报告分页可用
- 事件详情评论增删、点赞收藏可用
- 管理台关键 CRUD 可用

### 5.3 数据链路
- 抓取任务可触发
- 新事件能归属到正确社区
- 社区评分与报告可更新

## 6. 常见协作问题
- 修改数据库结构前，请在 PR 里说明迁移策略。
- 不要在前端写死临时业务数据；如需兜底，请明确注释“临时兜底”并附移除条件。
- 若发现历史乱码文本，请顺手修复为 UTF-8。

## 7. 安全与合规
- 不要提交真实密钥到仓库。
- `.env` 只保留本地，使用 `.env.example` 共享结构。
- 对外展示页面需保留“数据仅供参考”声明。
