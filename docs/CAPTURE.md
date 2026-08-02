# 网页双向捕获

[English](CAPTURE.en.md)

ContextVault 扩展既能推送资料，也能从用户已登录并明确授权的网页对话拉取信息。

## 两种拉取方式

1. **当前对话捕获：** 立即或定时读取当前页面。普通捕获只从用户消息提取候选，避免把模型幻觉当成用户事实。
2. **资料探测对话：** 绑定页面是空白新对话时，扩展自动询问该 AI 已记住哪些用户资料，等待回答稳定后拉取。平台回答按 `0.65` 置信度系数进入候选区，必须审阅，不能自动确认。

```bash
contextvault captures enable <account-id> \
  --interval 15 \
  --conversation-url https://chatgpt.com/ \
  --acknowledge-privacy-risk
contextvault captures list
```

## 自动推送

没有绑定对话的 route 会打开平台起始页创建新对话。第一次发送后，扩展等待页面产生稳定对话 URL，
再将其绑定到 route，后续增量复用该对话。消息附带 receipt 与 profile version 标记。

回执状态为 `prepared -> dispatching -> sent_unconfirmed -> completed`。一旦浏览器可能已经点击发送，
系统绝不自动重发；重启后先搜索页面标记恢复状态，找不到时要求用户在后台选择“已发送”或“未发送”。

连续三次页面适配失败会暂停该来源或 route，重新启用才会清除熔断。实验性服务商找不到安全选择器时
停止，不会扫描 Cookie、密码、全部历史列表或未授权标签页。
