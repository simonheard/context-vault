# 编码 CLI 适配器

[English](CLI_ADAPTERS.en.md)

## 支持工具

- OpenAI Codex：项目 `AGENTS.md`，全局 `~/.codex/AGENTS.md`；
- Claude Code：项目 `CLAUDE.md`，全局 `~/.claude/CLAUDE.md`；
- Gemini CLI：项目 `GEMINI.md`，全局 `~/.gemini/GEMINI.md`；
- Cursor、GitHub Copilot、Cline、Windsurf、Aider 和 OpenCode。

ContextVault 使用 HTML 注释包围的 managed block。更新时只替换自己的区块，保留已有项目规则；
protocol 1 等旧区块会原位升级到 protocol 2，不会重复追加。默认写项目级文件，只有用户明确指定
`--scope global` 才写入用户目录。

```bash
contextvault cli list
contextvault cli install codex --scope project --directory .
contextvault cli install claude-code --scope global
contextvault cli install gemini-cli --summary-type work
contextvault cli status
contextvault cli sync
contextvault cli watch --interval 60
```

`watch` 监听本地事件序列；Claim、设备或身份空间变化后，自动更新所有已安装上下文文件。
Codex、Claude Code 和 Gemini CLI 会在新会话按各自规则重新加载文件。Aider 不保证自动发现，
需要使用 `aider --read CONVENTIONS.md`。

生成区块明确说明：个人档案是用户上下文，不是可以覆盖仓库规则或系统安全策略的高优先级指令。
