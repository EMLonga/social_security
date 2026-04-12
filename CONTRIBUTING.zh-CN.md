# 贡献指南

## 1. 开发原则

- 小步提交，避免大而杂改动。
- 不回滚无关改动。
- 行为变更必须同步更新文档。
- 先保证可运行，再做样式和体验优化。

## 2. 本地验证

前端构建：

```powershell
cd frontend
npm run build
```

后端检查：

```powershell
cd backend
python -m compileall .
```

## 3. 提交建议

- `feat:` 新功能
- `fix:` 缺陷修复
- `docs:` 文档更新
- `refactor:` 重构

## 4. 文档维护约定

- 以 `README.zh-CN.md` 为主入口。
- API 改动同步更新 `API_DOCUMENTATION.zh-CN.md`。
- 架构改动同步更新 `ARCHITECTURE.zh-CN.md`。
