# 实现状态

[English](IMPLEMENTATION_STATUS.en.md)

## v0.7 本地闭环

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

## 需要外部平台或部署基础设施的能力

这些能力不能在没有目标平台授权、登录态或同步服务器的情况下由本地仓库独立完成：

- ChatGPT、Gemini、Claude 浏览器扩展和页面写入适配器；
- 各平台官方 API、文件上传、远程删除结果和同步后问答验证；
- 附件即时下载并转传到另一个已登录账号；
- 多设备端到端加密服务器、密钥恢复和设备撤销；
- 可选本地 LLM 与日历、联系人、代码仓库、智能家居连接器。

本地代码已经为这些功能提供 route、manifest、receipt、event cursor 和 provider adapter 边界。
接入时仍需分别遵守目标平台 API、账号政策和用户授权，不能保存 Cookie 后在服务器模拟登录。

## 可运行命令

```bash
contextvault import chatgpt-export.zip --account <account-id>
contextvault claims list
contextvault claims confirm-all
contextvault profile health
contextvault summary --type work
contextvault devices scan
contextvault routes add --from <source> --space personal --to <target>
contextvault routes preview <route-id>
contextvault privacy enable-sensitive
contextvault privacy consent <route-id> --categories health,finance --mode ask
contextvault sync run <route-id> --output gemini-profile.md
contextvault sync receipts
contextvault ui
```
