# 自动总结引擎

[English](MODEL_ENGINES.en.md)

内置确定性摘要始终可用。可选引擎包括 Ollama、LM Studio、其他 OpenAI-compatible endpoint、
已登录 Codex CLI 和 Claude Code。

```bash
contextvault models detect
contextvault summary --type personal --engine deterministic
contextvault summary --type work --engine ollama --model qwen3:8b
contextvault summary --type project --engine lmstudio --model <model-id>
contextvault summary --type personal --engine codex-cli --allow-cloud
```

Ollama 默认探测 `127.0.0.1:11434/v1`，LM Studio 默认探测 `127.0.0.1:1234/v1`。远程 endpoint
和已登录 CLI 必须明确允许云端处理；API Key 只从用户指定的环境变量读取，不进入数据库。

模型输入只包含已确认 Claim，并被标成不可信数据。输出必须是带有效 Claim ID manifest 的 JSON；未知
引用、空内容、超预算内容、秘密模式命中或无来源引用都会被拒绝。生成结果记录 engine、model、prompt
版本、输入 hash、输出版本和 Claim manifest，但不会反向修改标准档案。
