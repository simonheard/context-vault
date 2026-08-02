# 用户登录态浏览器扩展

[English](BROWSER_EXTENSION.en.md)

## 工作方式

扩展使用用户已经在 Chrome 中登录的受支持 AI 页面。ContextVault 不读取、
保存或上传密码、Cookie、OAuth Token 和 Session。扩展只执行以下操作：

1. 识别当前页面属于哪个受支持平台，并确认页面上存在可用输入框；
2. 在独立模式读取 Chrome Profile 内的轻量资料库，或在高级模式从 `127.0.0.1:8787` 读取路线；
3. 拉取用户授权的当前对话，或在空白页创建资料探测对话；
4. 显示最终文本、被策略阻止的字段和需要本次确认的敏感字段；
5. 半自动模式要求用户确认目标账号，填入后由用户发送；
6. 全自动模式创建或复用 route 专用对话，仅点击明确识别且可用的发送按钮；
7. 使用持久回执、页面标记和熔断器恢复中断，可能已点击时禁止自动重试。

网页结构变化导致输入框适配器失效时，用户仍可使用扩展的“复制”按钮或 CLI 生成 Markdown 文件。

## 安装

1. 打开 Chrome 的 `chrome://extensions`，开启“开发者模式”。
2. 点击“加载已解压的扩展程序”，选择仓库中的 `extension/` 目录。

   也可以运行 `python3 scripts/package_extension.py` 生成 `dist/contextvault-extension.zip`。
   GitHub Actions 的每次 `main` 构建也会生成同名 artifact。
3. 只使用网页能力时，选择“直接使用插件”。不需要安装 Python、CLI 或本地服务。
4. 需要 SQLite、多账号 route、本地模型和完整审计时，再启动可选服务：

   ```bash
   contextvault ui
   ```

5. 获取配对 Token：

   ```bash
   contextvault extension token
   ```

   也可以在管理后台的“隐私与授权”页面复制。

6. 把 Token 粘贴到扩展并保存。Token 只授权该扩展访问本机 ContextVault API。
7. 正常登录目标 AI，打开对话页面，然后点击扩展图标。

不再信任某个已配对扩展时，运行 `contextvault extension rotate-token`。所有旧 Token 会立即失效，
需要保留的扩展必须使用新 Token 重新配对。

## 使用前准备

独立模式无需预先创建账号或路线，每个 Chrome Profile 是一个隔离账号边界。高级连接模式至少需要一个目标账号和一条路线：

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
- 自动拉取默认关闭，必须逐账号确认；普通捕获只从用户消息提取，资料探测回答按低置信度候选处理；
- `prepared` 只表示内容已生成；点击发送前进入 `dispatching`，点击后先进入 `sent_unconfirmed`，完成本地确认后才记录 `completed`；
- 页面适配失败时安全停止，不尝试点击未知元素。
- 独立模式卸载前应导出 JSON；其存储不是端到端加密 vault，`sensitive` 默认不参与无人值守同步。

当前注册表覆盖 18 个国际与国产网页服务商，完整列表见[服务商适配矩阵](PROVIDERS.md)。页面 DOM
不是稳定 API，具体平台改变页面后可能退化为复制模式。附件即时转传仍需要平台文件选择器或官方 API。
