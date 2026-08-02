# 用户登录态浏览器扩展

[English](BROWSER_EXTENSION.en.md)

## 工作方式

扩展使用用户已经在 Chrome 中登录的 ChatGPT、Gemini 或 Claude 页面。ContextVault 不读取、
保存或上传密码、Cookie、OAuth Token 和 Session。扩展只执行以下操作：

1. 识别当前页面属于哪个受支持平台，并确认页面上存在可用输入框；
2. 从 `127.0.0.1:8787` 读取用户已配置路线的同步预览；
3. 显示最终文本、被策略阻止的字段和需要本次确认的敏感字段；
4. 要求用户确认当前网页登录的是路线指定的目标账号；
5. 将批准文本填入输入框，但不点击发送；
6. 用户检查并发送后，手动把 `prepared` 回执确认成 `completed`。

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
6. 正常登录 ChatGPT、Gemini 或 Claude，打开对话页面，然后点击扩展图标。

不再信任某个已配对扩展时，运行 `contextvault extension rotate-token`。所有旧 Token 会立即失效，
需要保留的扩展必须使用新 Token 重新配对。

## 使用前准备

至少需要一个目标账号和一条路线：

```bash
contextvault accounts add --platform gemini --label "个人 Gemini"
contextvault routes add --space personal --to <gemini-account-id>
```

扩展只显示目标平台与当前网页一致的启用路线。同一平台多个账号不会自动猜测；每次填入前必须确认
当前登录账号标签，以降低个人账号和工作账号串线风险。

## 安全边界

- API 默认只绑定 loopback；
- 扩展请求必须携带 vault 随机生成的配对 Token；
- Token 使用 Chrome 本地扩展存储，不是 AI 平台认证信息；
- 扩展不读取 Cookie、不抓取历史对话、不后台模拟登录；
- 不自动发送，不自动确认 `ask` 类敏感资料；
- `prepared` 只表示内容已生成或填入，用户确认发送后才记录 `completed`；
- 页面适配失败时安全停止，不尝试点击未知元素。

当前页面填入支持 ChatGPT、Gemini 和 Claude。附件即时转传仍需要每个平台单独提供文件选择或
官方上传 API；扩展不会绕过浏览器文件权限。
