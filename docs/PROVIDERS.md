# 服务商适配器

[English](PROVIDERS.en.md)

## 当前注册表

浏览器扩展 v0.4 注册了以下平台：

- 国际：ChatGPT、Gemini、Claude、Perplexity、Microsoft Copilot、Grok、Mistral Le Chat、Poe；
- 国产：DeepSeek、Kimi、通义千问/Qwen、豆包、腾讯元宝、智谱清言、文心一言/文小言、讯飞星火、天工 AI、海螺 AI。

每个适配器声明平台 ID、显示名称、官方页面 hostname、起始页面、输入框选择器、明确发送按钮
选择器、文件导入和自动发送能力。Python 服务和浏览器扩展分别维护注册表，并由自动化测试检查
服务端账号校验、扩展 manifest 和脚本语法。

## 稳定性边界

网页 DOM 不是稳定 API。半自动模式在找不到输入框时停止并允许复制文本；全自动模式只有在同时找到
已知输入框和已知发送按钮时才点击，通用 `button[type=submit]` 只能在输入框所属表单内使用。
ChatGPT、Gemini、Claude 和 DeepSeek 的当前对话拉取适配为 beta，其余平台为 experimental；所有平台都仍可能因 DOM 更新而失效。确定未发送的适配失败会记录为 `failed`；可能已经点击发送时进入 `dispatching` 或 `sent_unconfirmed`，等待页面标记恢复或用户处理，绝不自动重试。连续三次适配失败会熔断暂停。

用户可以运行 `contextvault providers` 查看服务端当前能力声明。新增平台需要同时增加：

1. `src/contextvault/providers.py` 服务端能力；
2. `extension/providers.js` 页面 hostname 和安全选择器；
3. `extension/manifest.json` 最小 host 权限；
4. 登录、输入框、发送按钮和失败降级测试。

ContextVault 不通过非官方镜像站登录，不保存账号凭证，也不会把一个平台的账号授权复制给另一个平台。
