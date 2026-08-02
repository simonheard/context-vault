# 用户登录态浏览器扩展

[English](BROWSER_EXTENSION.en.md)

## 工作方式

扩展使用用户已经在 Chrome 中登录的受支持 AI 页面。ContextVault 不读取、
保存或上传密码、Cookie、OAuth Token 和 Session。扩展只执行以下操作：

1. 识别当前页面属于哪个受支持平台，并确认页面上存在可用输入框；
2. 从 `127.0.0.1:8787` 读取用户已配置路线的同步预览；
3. 显示最终文本、被策略阻止的字段和需要本次确认的敏感字段；
4. 半自动模式要求用户确认目标账号，填入后由用户发送；
5. 全自动模式按路线间隔打开或复用目标页面，仅点击明确识别且可用的发送按钮；
6. 发送成功记录 `completed`；页面探测失败记录 `failed`，等待下一轮安全重试。

网页结构变化导致输入框适配器失效时，用户仍可使用扩展的“复制”按钮或 CLI 生成 Markdown 文件。

## 安装

1. 启动本地服务：

   ```bash
   contextvault ui
   ```

2. 打开 Chrome 的 `chrome://extensions`，开启“开发者模式”。
3. 点击“加载已解压的扩展程序”，选择仓库中的 `extension/` 目录。

   也可以运行 `python3 scripts/package_extension.py` 生成 `dist/contextvault-extension.zip`。
   GitHub Actions 的每次 `main` 构建也会生成同名 artifact。
4. 获取配对 Token：

   ```bash
   contextvault extension token
   ```

   也可以在管理后台的“隐私与授权”页面复制。

5. 把 Token 粘贴到扩展并保存。Token 只授权该扩展访问本机 ContextVault API。
6. 正常登录目标 AI，打开对话页面，然后点击扩展图标。

不再信任某个已配对扩展时，运行 `contextvault extension rotate-token`。所有旧 Token 会立即失效，
需要保留的扩展必须使用新 Token 重新配对。

## 使用前准备

至少需要一个目标账号和一条路线：

```bash
contextvault accounts add --platform gemini --label "个人 Gemini"
contextvault routes add --space personal --to <gemini-account-id>
```

扩展只显示目标平台与当前网页一致的启用路线。半自动模式要求每次确认账号；全自动模式无法可靠读取
平台账号身份，因此启用前必须确认风险，并建议每个 Chrome Profile 只登录一个目标账号。

## 安全边界

- API 默认只绑定 loopback；
- 扩展请求必须携带 vault 随机生成的配对 Token；
- Token 使用 Chrome 本地扩展存储，不是 AI 平台认证信息；
- 扩展不读取 Cookie、不抓取历史对话、不后台模拟登录；
- 全自动默认关闭，必须逐路线确认风险；永不发送 `secret`，也不自动批准 `ask` 类敏感资料；
- `prepared` 只表示内容已生成或填入，用户确认发送后才记录 `completed`；
- 页面适配失败时安全停止，不尝试点击未知元素。

当前注册表覆盖 18 个国际与国产网页服务商，完整列表见[服务商适配矩阵](PROVIDERS.md)。页面 DOM
不是稳定 API，具体平台改变页面后可能退化为复制模式。附件即时转传仍需要平台文件选择器或官方 API。
