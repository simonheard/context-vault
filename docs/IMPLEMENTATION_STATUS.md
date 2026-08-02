# 实现状态

[English](IMPLEMENTATION_STATUS.en.md)

## v0.12 独立运行、一键合并连接与双向自动化

以下能力已经可以通过 CLI 或本地管理后台运行：

- 解析 ChatGPT 官方 ZIP 或 `conversations.json`；
- 保存来源账号、会话、消息和内容 hash，重复导入自动去重；
- 在证据入库前检测常见密码、私钥、API key、Cookie 和 Token，命中后整体脱敏；
- 通过不执行聊天中任何指令的确定性中英文规则提取资料候选；
- 候选确认、批量确认、拒绝、冲突、删除、全文搜索和来源追踪；
- Markdown/JSON 标准档案、工作、项目、设备和最近变化摘要；
- 多 AI 账号、身份空间、账号断开/撤销和来源—空间—目标路线；
- 本机型号、OS、CPU、内存和开发工具版本扫描，不读取环境变量值或认证文件；
- 全局敏感同步开关、路线级类别/敏感级别/字符预算策略和知情同意回执；
- 同步预览、被阻止字段、逐次确认、增量 diff、Markdown 资料包和同步回执；
- 附件引用、已批准提取文本和即时转传适配器边界；数据库不保存附件二进制；
- 只追加事件日志、多设备增量游标、资料健康度和 schema 迁移。
- 18 个国际与国产网页服务商的统一注册表和 Chrome MV3 页面适配；
- 半自动预览/填入，以及逐路线风险确认、定时调度、安全按钮探测、失败重试的全自动模式；
- Codex、Claude Code、Gemini CLI 等九种编程助手的项目级/全局托管资料块；
- macOS LaunchAgent、Linux systemd user service 和 Windows Task Scheduler 常驻服务定义；
- protocol 3 / schema 9 协商、每客户端 Token、Origin/Host/JSON 校验和 DNS-rebinding 防护；
- 当前对话拉取、空白页资料探测、低置信度候选、专用推送对话绑定和三次失败熔断；
- `dispatching` / `sent_unconfirmed` 回执、页面标记与重启恢复，避免不确定发送被重复执行；
- 确定性、Ollama、LM Studio、OpenAI-compatible、Codex CLI 和 Claude Code 总结引擎。
- 不依赖 Python 的扩展独立资料库、候选审阅、JSON 备份、捕获和推送调度器；
- 不包含扩展目录的独立 CLI wheel，以及扩展备份到 SQLite 的显式迁移命令。
- 8 位、十分钟、一次性、五次失败锁定的扩展链接码；连接时自动去重合并，断开时先生成最新独立快照。

## 需要外部平台或部署基础设施的能力

这些能力不能在没有目标平台授权、登录态或同步服务器的情况下由本地仓库独立完成：

- 各平台官方 API、文件上传、远程删除结果和同步后问答验证；
- 平台完整历史列表批量读取（当前只读明确绑定的对话或官方导出）；
- 附件即时下载并转传到另一个已登录账号；
- 多设备端到端加密同步服务器、密钥恢复和设备撤销（当前已实现事件游标和协议边界）；
- 可选本地 LLM 与日历、联系人、代码仓库、智能家居连接器。

本地代码已经为这些功能提供 route、manifest、receipt、event cursor 和 provider adapter 边界。
接入时仍需分别遵守目标平台 API、账号政策和用户授权，不能保存 Cookie 后在服务器模拟登录。

## 可运行命令

```bash
contextvault import chatgpt-export.zip --account <account-id>
contextvault link
contextvault import contextvault-browser.json --format browser-vault
contextvault claims list
contextvault claims confirm-all
contextvault profile health
contextvault profile export-browser contextvault-browser.json
contextvault summary --type work
contextvault devices scan
contextvault routes add --from <source> --space personal --to <target>
contextvault routes preview <route-id>
contextvault privacy enable-sensitive
contextvault privacy consent <route-id> --categories health,finance --mode ask
contextvault sync run <route-id> --output gemini-profile.md
contextvault sync receipts
contextvault routes automation <route-id> --mode full --interval 60 --acknowledge-data-risk
contextvault cli install codex --scope project
contextvault cli sync
contextvault daemon install
contextvault models detect
contextvault captures enable <account-id> --acknowledge-privacy-risk
contextvault ui
```
