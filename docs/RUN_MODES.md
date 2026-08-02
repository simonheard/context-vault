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
python -m pip install context_vault-0.12.0-py3-none-any.whl
contextvault-cli init
contextvault-cli import chatgpt-export.zip
contextvault-cli claims confirm-all
contextvault-cli summary --type personal
contextvault-cli cli install codex --scope project
```

CLI 使用本地 SQLite，支持官方导出、资料审阅、设备、摘要、路由和编程助手文件适配。只有执行 `ui`、
`daemon`、`captures` 或 `extension` 相关命令时才会启用网页服务协作能力。

## 可选的高级连接模式

需要 SQLite 全量审计、多账号 route、服务端策略、本地模型或跨客户端事件时，两者可以一起使用：

```bash
contextvault link
```

终端显示 8 位短码并启动 loopback 服务。在扩展中输入短码，点击“合并并连接”即可。短码十分钟过期、
只能使用一次，连续五次错误后作废；长 Token 只保留为高级备用方式。

连接时，扩展把独立资料按“属性 + 内容”去重合并进 SQLite，保留候选/已确认状态，并为当前网页平台创建
一个自动发送关闭、敏感资料阻止的安全默认账号与路线，然后切换为连接模式。以后打开新平台时，只需点击
“为当前平台创建默认账号与路线”。
从此 SQLite 是唯一主资料库，扩展负责网页捕获和推送，不再同时修改独立副本。点击“断开并独立使用”时，
扩展先从 SQLite 拉取最新快照、撤销当前客户端 Token，再回到独立模式。失败时不删除任何一侧的数据。

JSON `import` / `export-browser` 继续作为离线迁移和备份方式。
