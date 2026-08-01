# 多账号设计

[English](MULTI_ACCOUNT.en.md)

## 目标

同一用户可以在同一平台拥有多个账号，例如个人 ChatGPT、工作 ChatGPT、个人 Gemini 和公司
Gemini。系统必须准确记录每条证据来自哪个账号、每次同步发给哪个账号，并防止资料意外串线。

## 核心模型

```text
ProviderAccount（来源）
        |
        v
ProfileSpace（个人 / 工作 / 客户 / 匿名）
        |
        v
Canonical Claims
        |
        v
SyncRoute + Policy
        |
        v
ProviderAccount（目标）
```

### ProviderAccount

表示一个平台账号引用：

- 平台：ChatGPT、Gemini、Claude 等；
- 本地标签：`个人 Gemini`、`公司 ChatGPT`；
- 可选的不可逆账号标识 hash；
- 状态：active、disconnected、revoked；
- 最近识别与同步时间。

不保存密码、Cookie、OAuth token 或 session。实际登录仍由浏览器或未来的系统凭证存储处理。

### ProfileSpace

资料隔离空间，例如：

- `personal`：个人生活和通用偏好；
- `work`：当前公司、公司设备和内部项目；
- `client/acme`：特定客户资料；
- `anonymous`：不包含真实身份的偏好集。

一条 Claim 可以属于一个或多个明确授权的空间，但不能因为账号属于同一用户就自动混合。

### SyncRoute

定义来源、档案空间和目标：

```text
个人 ChatGPT -> personal -> 个人 Gemini
工作 ChatGPT -> work -> 公司 Gemini
MacBook Agent -> personal + work(选定字段) -> 指定目标
```

每条 route 拥有独立的类别白名单、敏感模式、自动同步设置和摘要预算。

## 账号识别

浏览器扩展应在执行前显示当前平台和本地账号标签。若检测到账号发生变化，应暂停同步并要求
用户确认，而不是根据域名假设仍是原账号。

账号 email 等标识只在必要时本地显示；持久化时优先保存不可逆 hash 和用户定义标签。

## 防串线规则

1. 新账号默认没有任何 SyncRoute。
2. 工作空间默认不能同步到个人账号。
3. 敏感授权不能从一个账号复制到另一个账号。
4. 更换目标账号会触发重新同意。
5. 同步预览必须显示目标平台和账号标签。
6. 每条 SyncReceipt 必须绑定具体账号和 route。
7. 无法可靠确认当前网页账号时禁止自动写入。

## 账号生命周期

- **连接：** 创建本地引用并选择所属空间，不立即同步历史资料；
- **重命名：** 只修改本地标签，不改变身份；
- **断开：** 停止读取和写入，保留审计记录；
- **撤销：** 禁用 route 和同意，提示远程数据可能仍然存在；
- **删除本地引用：** 需要先处理相关来源、回执和纠正任务。

## 规划命令

```text
contextvault accounts list
contextvault accounts add chatgpt --label personal-chatgpt
contextvault accounts rename <id> --label work-chatgpt
contextvault accounts disconnect <id>
contextvault spaces list
contextvault spaces create work
contextvault routes add --from <account> --space work --to <account>
contextvault routes preview <route>
```

