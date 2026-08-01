# 附件引用与跨 AI 处理

[English](ATTACHMENTS.en.md)

## 架构决定

ContextVault 的数据库只保存文本、结构化资料、附件引用、同步策略和审计记录。原始附件继续
由 ChatGPT、Gemini、Claude 等 AI 提供商托管。ContextVault 默认不提供 R2、S3 或其他
对象存储，也不承担原始文件的长期备份责任。

## AttachmentRef

不能只保存远程 URL，因为 URL 可能临时有效、依赖登录状态或绑定具体账号。附件身份应由平台、
来源账号和平台文件 ID 共同确定。

```text
attachment_refs
- id
- vault_id
- provider_account_id
- provider
- provider_file_id
- conversation_id
- message_id
- remote_url              # 临时缓存，不是永久身份
- filename
- mime_type
- size_bytes
- sha256                  # 能获取时用于去重
- description
- extracted_text          # 用户允许时保存
- sensitivity
- status                  # active / missing / expired / denied
- last_verified_at
- created_at
```

`provider_account_id` 是必需边界。同一个 ChatGPT 平台上的个人账号与工作账号不能共享附件权限。

## 三种同步模式

### 只同步引用

目标 AI 只收到附件名称、类型、来源、说明和状态，不收到文件内容。

```text
附件：2025 Tax Return.pdf
来源：个人 ChatGPT
类型：PDF
说明：2025 年报税材料
状态：文件仍保存在 ChatGPT，未向当前目标发送
```

适合只需要记录“存在这个文件”的场景。

### 同步提取文本

用户允许后，由本地 Agent 读取文件、提取文本、执行秘密检测和脱敏，再把批准的文本或摘要
存入数据库并发送给目标 AI。原始文件不保存。

```text
来源附件 -> 本地临时读取 -> 文本提取 -> 脱敏与预览
         -> extracted_text -> 目标资料包
```

提取文本继承原附件的敏感级别和账号/身份空间边界。

### 用户触发即时转传

浏览器扩展或本地 Agent 在用户明确操作时，从来源账号读取附件并上传到目标账号。文件只在内存
或受限临时目录存在，完成或失败后立即删除。数据库只保存来源与目标 `AttachmentRef`、结果和
同步回执。

## 引用状态

- `active`：当前账号和设备仍能访问；
- `reauth_required`：需要重新登录来源账号；
- `expired`：临时 URL 失效，但平台文件 ID 可能仍可解析；
- `missing`：来源文件已删除或无法找到；
- `permission_denied`：当前账号无权访问；
- `device_unavailable`：只能从另一台设备或浏览器会话读取；
- `copied`：目标平台已经拥有自己的文件引用。

后台应定期或在使用前验证引用，但不能频繁下载文件只为了检查状态。

## 多设备限制

新设备即使同步到了 `AttachmentRef`，也不一定能读取文件，因为它可能没有登录相同的提供商
账号。管理后台必须区分“知道附件存在”和“当前设备有能力读取附件”。

## 隐私规则

- 附件引用本身也可能敏感，例如文件名、会话标题和账号标签；
- 提取文本前必须显示文件、目标和敏感风险；
- `secret` 检测命中时拒绝保存提取文本和自动转传；
- 即时转传不得写入长期缓存、日志或崩溃报告；
- 临时文件使用随机名称、限制权限，并在成功、失败和进程退出时清理；
- 同步回执记录发送了哪个附件，但不复制文件内容。

## 失败和恢复

附件不可用时，系统应保留引用和来源信息，允许用户：

- 在正确账号中重新认证；
- 从仍可访问的设备重新解析；
- 手动重新选择文件；
- 只同步已有描述或提取文本；
- 将引用标为永久丢失。

## 后续可选外部存储

如果用户需要独立备份，可连接用户自己的 S3、WebDAV、Google Drive 或其他存储。它应是可选
连接器，并使用独立授权和加密策略，不能悄悄变成 ContextVault 默认文件仓库。

