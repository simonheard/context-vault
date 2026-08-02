# Automatic summary engines

[中文](MODEL_ENGINES.md)

The deterministic renderer is always available. Optional engines include Ollama, LM Studio, another OpenAI-compatible endpoint, a signed-in Codex CLI, and Claude Code.

```bash
contextvault models detect
contextvault summary --type personal --engine deterministic
contextvault summary --type work --engine ollama --model qwen3:8b
contextvault summary --type personal --engine codex-cli --allow-cloud
```

Ollama is probed at `127.0.0.1:11434/v1` and LM Studio at `127.0.0.1:1234/v1`. Remote endpoints and signed-in CLIs require explicit cloud consent. API keys are read only from a user-named environment variable and are never stored in the database.

Model input contains confirmed claims marked as untrusted data. Output must be JSON with a valid claim-ID manifest. Unknown citations, empty or over-budget output, secret-pattern matches, and uncited results are rejected. Generated summaries record the engine, model, prompt version, input hash, output version, and claim manifest without modifying the canonical profile.
