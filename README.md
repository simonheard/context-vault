# ContextVault

[English](README.en.md)

ContextVault 是一个**跨 AI 的个人记忆与用户资料同步工具**。

它从 ChatGPT、Gemini、Claude 等 AI 的历史对话中自动识别它们已经了解的用户信息，
整理成一份持续更新、来源可追溯的个人资料，再按用户设定同步给其他 AI。

例如：

- 年龄、生日、所在地、语言；
- 就读学校、专业、工作单位、职位和技能；
- 回答风格、写作习惯、饮食或出行偏好；
- 正在做的项目、长期目标和已经做出的决定；
- 拥有的电脑、手机、服务器和智能设备；
- 每台设备的型号、操作系统、软件、开发环境与非敏感配置。

> 让每个 AI 都能在用户允许的范围内认识同一个你。

## 它不是聊天备份工具

原始聊天只是信息来源之一，最终产品不是把所有聊天复制到另一个平台，而是维护一份
结构化、可验证、会随时间变化的“个人记忆档案”。

```text
ChatGPT 历史对话       设备扫描       手动填写       其他数据源
         \                |              |              /
          ----> 自动提取与变化检测 / 冲突处理 <----
                              |
                              v
                   用户画像 + 设备与环境资料
                              |
                   审阅、权限与同步策略
                       /      |       \
                      v       v        v
                  Gemini   Claude   其他 AI
```

## 核心能力

1. **自动发现资料：** 从长期聊天中提取关于用户的事实、偏好、关系、目标和环境信息。
2. **持续更新：** 识别“换工作”“搬家”“更换电脑”等变化，而不是无限追加旧信息。
3. **来源与时间：** 每条资料保留原始对话、时间、置信度和有效期。
4. **冲突处理：** 新旧信息冲突时进行合并、过期或请求用户确认。
5. **设备同步：** 本地 Agent 采集硬件、系统、软件和允许同步的配置，但不采集密钥。
6. **自动总结：** 生成简版用户简介、完整个人档案、项目资料包或设备环境说明。
7. **按目标同步：** 对 Gemini、Claude 等目标分别设置同步字段、敏感级别和更新频率。
8. **隐私优先：** 默认本地处理；高敏感资料和首次跨平台发送必须明确确认。
9. **敏感同步开关：** 可按 AI 平台和资料类别选择永不发送、每次询问或允许自动同步。
10. **多账号隔离：** 个人、工作和客户账号分别建立同步路径，避免资料串线。
11. **本地管理后台：** 在一个简单 GUI 中管理资料、账号、身份空间、设备、隐私和同步历史。
12. **附件引用：** 数据库只保存附件元数据、提供商引用和可选提取文本，不长期保存原文件。

## 第一版要完成什么

最小闭环不是全文搜索，而是：

```text
导入 ChatGPT 数据
  -> 自动提取用户资料候选
  -> 用户一次性审阅
  -> 生成标准个人档案
  -> 生成 Gemini 可用的资料摘要
  -> 后续对话发生变化时增量更新
```

第一版优先支持：

- ChatGPT 官方导出解析；
- 身份、教育、工作、所在地、偏好、技能、项目和设备信息提取；
- 候选资料确认与冲突处理；
- Markdown/JSON 个人档案；
- Gemini 资料包与复制/注入流程；
- 本地设备基本信息采集；
- 变更摘要和同步预览。

## 当前仓库状态

当前已经具备可运行的本地完整闭环和用户登录态适配器（v0.8.0），包含：

- 零依赖 Python CLI；
- SQLite 资料库与显式领域模型，核心对象为 `Entity`、`Claim`、`ProviderAccount`、`ProfileSpace` 和 `AttachmentRef`；
- 候选资料的添加、确认、拒绝，以及 Markdown/JSON 标准档案生成；
- 多账号与身份空间管理；
- 只保存提供商文件引用的附件登记；
- 只追加同步事件日志和多设备游标基础；
- 禁止保存秘密级数据的仓储层校验；
- 可操作的本地管理 GUI，以及覆盖核心闭环的自动化测试。
- ChatGPT 官方导出解析、入库前秘密脱敏和确定性中英文候选提取；
- 设备扫描、同步策略、预览 diff、资料包、知情同意与同步回执。
- Chrome 用户侧扩展：在用户自己登录的 ChatGPT、Gemini、Claude 页面填入已批准资料，不接触认证凭证且不自动发送。

## 快速开始

需要 Python 3.11+。

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
contextvault init
contextvault status
contextvault doctor
contextvault ui
contextvault accounts add --platform chatgpt --label "个人 ChatGPT"
contextvault claims add identity.location "New York"
contextvault claims list
contextvault claims confirm <claim-id>
contextvault profile show
contextvault events list
contextvault import chatgpt-export.zip
contextvault devices scan
contextvault routes preview <route-id>
contextvault sync run <route-id> --output gemini-profile.md
contextvault extension token
python3 -m unittest discover -s tests
```

## 后续规划命令

```text
浏览器扩展捕获用户主动批准的增量对话
各平台官方 API 与附件上传适配器
端到端加密多设备同步服务器
可选本地 LLM 与外部数据连接器
```

## 文档

- [产品计划](docs/PRODUCT_PLAN.md)
- [技术架构](docs/ARCHITECTURE.md)
- [用户资料与记忆模型](docs/MEMORY_MODEL.md)
- [敏感信息同步与知情同意](docs/PRIVACY_POLICY.md)
- [多账号设计](docs/MULTI_ACCOUNT.md)
- [设计建议与优先级](docs/DESIGN_RECOMMENDATIONS.md)
- [本地管理后台](docs/GUI.md)
- [附件引用与跨 AI 处理](docs/ATTACHMENTS.md)
- [实现状态与外部集成边界](docs/IMPLEMENTATION_STATUS.md)
- [用户登录态浏览器扩展](docs/BROWSER_EXTENSION.md)
