# 用户资料与记忆模型

[English](MEMORY_MODEL.en.md)

## 为什么使用 Claim

“用户 28 岁”不是一条永远有效的文本记忆。系统应尽可能保存“出生年份为 1998”，保留来源，
并在需要时计算年龄。同样，“在某公司工作”“住在纽约”“使用 MacBook”都需要时间范围、
来源和当前状态。

因此最小单位是 Claim：关于一个实体、一个属性、一个值的带证据陈述。

## 属性分类

```text
identity.*          姓名、生日、语言、时区
location.*          国家、城市、常用地点
education.*         学校、专业、学历、课程、证书
employment.*        公司、职位、团队、职责、工作方式
preference.*        回答、写作、代码、饮食、旅行、购物
skill.*             技能、熟练度、学习状态
goal.*              短期与长期目标
project.*           项目、技术栈、状态、决定、任务
relationship.*      用户确认的重要人物和关系
device.*            型号、硬件、系统、软件、配置
event.*             搬家、入职、毕业、购买设备
health.*            高敏感，默认禁止自动同步
finance.*           高敏感，默认禁止自动同步
legal.*             高敏感，默认禁止自动同步
```

## 敏感级别

- `public`：用户愿意公开的信息；
- `personal`：一般个人资料，可按目标策略同步；
- `private`：默认需要预览；
- `sensitive`：每次跨平台同步需明确确认；
- `secret`：拒绝存储。

敏感级别描述数据本身；同步模式描述用户对某个目标的授权，两者不能混为一谈。

- `block`：永不发送；
- `ask`：每次同步前逐项确认；
- `allow`：在指定目标和类别内允许自动同步；
- `secret` 数据始终强制 `block`，用户不能覆盖。

## 自动化规则

- 用户明确说“我现在在 X 工作”且无冲突：一般资料可进入批量确认。
- AI 推断“你可能住在 X”：保持 `candidate`，不能自动同步。
- 设备 Agent 确定性读取 OS 版本：可按白名单自动确认。
- 新 Claim 与当前 Claim 冲突：创建冲突，不覆盖。
- 新信息带明确变化表达：旧 Claim 标为 `superseded` 并结束有效期。
- 同一事实来自多个独立来源：提高置信度，但不删除来源记录。

## 目标同步策略示例

```json
{
  "target": "gemini",
  "allowed_categories": [
    "identity.language",
    "education.current",
    "employment.current",
    "preference.response",
    "skill",
    "project.active",
    "device.summary"
  ],
  "max_sensitivity": "personal",
  "sensitive_mode": "ask",
  "require_preview_on_first_sync": true,
  "auto_sync_low_risk_changes": true,
  "summary_budget_chars": 12000
}
```

开启敏感同步只影响未来操作。撤销授权可以停止后续同步，但无法保证目标 AI 已经忘记此前收到
的内容；系统应提供发送历史和纠正/删除操作说明。

## 设备配置边界

允许采集：型号、OS、CPU、内存、磁盘容量、已批准的软件、语言版本、包管理器、容器工具、
编辑器、项目别名和非敏感设置。

默认禁止：密码、私钥、API key、Cookie、浏览器 token、环境变量值、Wi-Fi 密码、完整序列号、
恢复密钥和私密文件内容。
