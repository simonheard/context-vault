# ContextVault

[English](README.en.md)

ContextVault 是一个本地优先、由用户掌控的 AI 上下文库。它把不同 AI 产品的导出
数据转换成可搜索、可审计、可迁移的统一格式，并让用户在发送给其他 AI 之前明确
预览和确认内容。

> 你的 AI 上下文属于你，而不是某个 AI 平台。

## 产品边界

本项目不承诺“自动同步所有聊天”，也不承诺在另一个平台原样恢复会话列表。第一阶段
聚焦稳定的官方导出、标准化数据模型、本地搜索、敏感信息检查和便携式上下文包。
浏览器增量捕获与端到端加密多设备同步将在核心流程验证后实现。

## 产品原则

- **本地优先：** 解析、索引和审阅默认在用户设备完成。
- **明确授权：** 保存或发送前展示具体内容。
- **来源可追溯：** 每条记忆保留来源、时间、置信度、作用域、敏感级别与生命周期状态。
- **适配器隔离：** 平台格式变化不污染内部模型。
- **不保存凭证：** 只允许记录凭证位置，不保存密码、密钥或会话令牌。
- **诚实迁移：** 让历史可搜索、可作为上下文使用，而不是承诺原生恢复。

## 当前状态

当前是规划与基础骨架阶段，包含：

- 零依赖 Python CLI；
- 支持 FTS5 的 SQLite vault；
- 产品路线图、架构与风险说明；
- vault 初始化与状态测试。

## 快速开始

需要 Python 3.11+。

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
contextvault init
contextvault status
contextvault doctor
python3 -m unittest discover -s tests
```

默认 vault 路径为 `.contextvault/vault.sqlite`；可使用 `--vault PATH` 覆盖。

## 命令路线图

```text
contextvault init
contextvault status
contextvault doctor
contextvault import <export.zip> --source chatgpt|claude|gemini
contextvault inspect
contextvault search <query>
contextvault extract-memories
contextvault redact
contextvault export --target markdown|json|claude|gemini|chatgpt
```

当前仅实现 `init`、`status` 和 `doctor`。

## 文档

- [产品计划](docs/PRODUCT_PLAN.md)
- [技术架构](docs/ARCHITECTURE.md)

