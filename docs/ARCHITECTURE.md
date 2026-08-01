# 技术架构

[English](ARCHITECTURE.en.md)

## 总体结构

```text
┌──────────────────── 数据来源 ────────────────────┐
│ AI 官方导出 │ 浏览器扩展 │ 本地设备 Agent │ 手动输入 │
└──────────────────────┬──────────────────────────┘
                       v
┌──────────────── 采集与标准化层 ─────────────────┐
│ Source Adapter │ 解析 │ 去重 │ 秘密检测 │ 实体识别 │
└──────────────────────┬──────────────────────────┘
                       v
┌──────────────── 资料理解与合并层 ───────────────┐
│ Claim 提取 │ 时间判断 │ 冲突检测 │ 置信度 │ 审阅队列 │
└──────────────────────┬──────────────────────────┘
                       v
┌──────────────── 标准个人档案 ───────────────────┐
│ User │ Education │ Work │ Preference │ Project  │
│ Person │ Device │ Environment │ Goal │ Timeline │
└───────────────┬──────────────────────┬───────────┘
                v                      v
        Summary Generator        Sync Policy Engine
                \                      /
                 v                    v
           Gemini │ Claude │ ChatGPT │ 其他目标
```

## 真相、证据和同步副本

系统必须区分三种东西：

1. **证据：** 原始聊天消息、设备扫描或手动输入。
2. **标准档案：** 合并、确认并带有效期的当前用户资料，是系统真相来源。
3. **同步副本：** 某个平台根据策略收到的摘要或字段子集。

不能直接把一次 LLM 总结当作真相，也不能把 Gemini 已收到的副本反向覆盖标准档案。

## 核心数据对象

### Entity

用户本人、学校、公司、人物、项目、设备或地点。设备也是实体，因此可以拥有别名、关系、
时间线和独立 Claim。

### Claim

关于某个实体的单一可验证陈述。字段包括：

- `entity_id`、`attribute` 和结构化 `value_json`；
- 来源平台、会话、消息或扫描 ID；
- `confidence`、`status`、`sensitivity`；
- `valid_from`、`valid_until`、`observed_at`；
- 创建时间、更新时间和确认人。

Claim 状态：

```text
candidate -> confirmed -> superseded -> expired
     |            |             |
     v            v             v
  rejected     conflicted     deleted
```

### Device

设备实体的结构化扩展，包含类型、稳定指纹、最后在线时间和可同步配置。硬件序列号、完整 IP、
用户名和路径等字段要按敏感策略处理。

### SyncTarget

目标平台及账号标签，不保存登录凭证。保存允许类别、敏感级别、摘要预算、同步方式、上次同步
版本和时间。

### SyncReceipt

记录某次同步向某个平台发送了哪些 Claim、使用了哪个摘要版本、是否成功，以及后续如何撤销
或纠正。

## 提取流水线

```text
原始消息
 -> 消息清理与角色识别
 -> 与“用户本人”相关的片段召回
 -> 结构化候选提取
 -> schema 验证
 -> 实体解析与去重
 -> 与现有 Claim 比较
 -> 新增 / 确认 / 冲突 / 使旧值过期
 -> 审阅队列或自动确认
```

LLM 适合从自然语言中提出候选，但确定性代码负责 schema 校验、时间计算、秘密拒绝、去重和
策略执行。身份、医疗、法律、财务和关系推断不得自动确认。

## 设备 Agent

设备扫描分层进行：

- **基础层：** 设备类型、型号、CPU、内存、OS 和版本；
- **开发层：** shell、编辑器、语言运行时、包管理器、容器与 Git；
- **软件层：** 用户允许列出的应用；
- **配置层：** 只采集白名单键，默认排除环境变量值和认证文件；
- **项目层：** repo 名称、技术栈和目录别名，不默认上传源代码。

Agent 先生成本地 diff，用户策略决定哪些变化进入标准档案、哪些允许同步给 AI。

## 摘要生成

摘要不是唯一存储格式，而是标准档案的可重建视图。生成器接受：

- 目标平台；
- 使用场景；
- 允许的资料类别和敏感上限；
- token/字符预算；
- 上次同步版本。

输出包括完整摘要和变更摘要，并附带机器可读 manifest，列出包含的 Claim ID。

## 同步方式

按稳定性排序：

1. 官方 API 或官方导入格式；
2. 用户触发的文件导入；
3. 一键复制结构化资料；
4. 浏览器扩展在用户已登录页面中注入；
5. 不支持服务器保存 Cookie 后模拟登录。

## 本地存储

```text
.contextvault/
  vault.sqlite
  sources/<source-id>/manifest.json
  artifacts/<sha256-prefix>/<sha256>
  summaries/<target>/<version>.md
  sync-receipts/<target>/<version>.json
  config.toml
```

SQLite 负责实体、Claim、设备、目标、版本、FTS 和关系。附件使用内容寻址存储。后续向量索引
是可重建缓存，不是真相来源。

## 加密与服务器

默认完全本地。多设备同步阶段使用每个 vault 的随机密钥和 XChaCha20-Poly1305；用户秘密经
Argon2id 派生包装密钥。服务器只保存密文对象、版本和最少路由元数据，不能读取个人资料。

## 模块建议

```text
contextvault/
  domain/        # entity, claim, device, policy, receipt
  importers/     # chatgpt, claude, gemini, files
  extractors/    # profile, timeline, device references
  merge/         # identity resolution, conflict, validity
  summaries/     # personal, work, project, devices
  targets/       # gemini, claude, chatgpt
  device_agent/  # platform scanners and allowlists
  storage/       # sqlite, artifacts, migrations
  cli/           # commands and review UI
```

