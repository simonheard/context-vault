# 独立运行模式

[English](RUN_MODES.en.md)

ContextVault 提供两个可分别安装、分别运行的产品面。两者没有强制依赖，也不会在后台自动合并资料。

## 浏览器扩展独立模式

直接安装 `contextvault-extension.zip`，选择“直接使用插件”，不需要 Python、CLI、Codex 或本地 HTTP 服务。

- 最多 5000 条文本 Claim、配置和 200 条回执保存在当前 Chrome Profile 的 `chrome.storage.local`；
- 可拉取当前对话、在空白页创建资料探测对话、审阅候选、生成资料包、填入或自动推送；
- 待审阅候选不会发送，`secret` 拒绝保存，`sensitive` 默认不进入无人值守同步；
- 连续三次页面失败熔断；可能已经发送的任务暂停且不自动重试；
- 每个 Chrome Profile 视为独立账号边界。要同时使用同一平台多个账号，使用多个 Chrome Profile；
- 卸载扩展或清除扩展数据前必须导出 JSON 备份。Chrome 存储不是端到端加密保险库，静态保护依赖操作系统磁盘加密。

扩展管理页支持确认、拒绝、手工添加、导入和导出。导出的 schema 1 JSON 可迁移到 CLI：

```bash
contextvault-cli import contextvault-browser-2026-08-02.json --format browser-vault
contextvault-cli profile export-browser contextvault-browser.json
```

## CLI 独立模式

安装 `context_vault-*.whl` 后只使用 `contextvault-cli`。浏览器扩展、Chrome 和网页管理后台均不是必需条件。

```bash
python -m pip install context_vault-0.11.0-py3-none-any.whl
contextvault-cli init
contextvault-cli import chatgpt-export.zip
contextvault-cli claims confirm-all
contextvault-cli summary --type personal
contextvault-cli cli install codex --scope project
```

CLI 使用本地 SQLite，支持官方导出、资料审阅、设备、摘要、路由和编程助手文件适配。只有执行 `ui`、
`daemon`、`captures` 或 `extension` 相关命令时才会启用网页服务协作能力。

## 可选的高级连接模式

需要 SQLite 全量审计、多账号 route、服务端策略、本地模型或跨客户端事件时，扩展可切换为“连接本地服务”。
这不会自动复制独立资料库；用户通过 `import --format browser-vault` 或 `profile export-browser` 显式迁移，避免两份资料在不知情时互相覆盖。
