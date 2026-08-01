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

当前是产品与数据模型基础阶段，包含：

- 零依赖 Python CLI；
- SQLite 资料库，核心对象为 `Entity`、`Claim`、`Device` 和 `SyncTarget`；
- 用户资料模型、产品路线图、安全边界和系统架构；
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

## 规划命令

```text
contextvault import chatgpt-export.zip
contextvault extract-profile
contextvault review
contextvault profile show
contextvault devices scan
contextvault diff
contextvault sync add gemini
contextvault sync preview gemini
contextvault sync run gemini
contextvault privacy show
contextvault privacy set --target gemini --sensitive ask
contextvault summary --type personal
contextvault summary --type devices
```

## 文档

- [产品计划](docs/PRODUCT_PLAN.md)
- [技术架构](docs/ARCHITECTURE.md)
- [用户资料与记忆模型](docs/MEMORY_MODEL.md)
- [敏感信息同步与知情同意](docs/PRIVACY_POLICY.md)
