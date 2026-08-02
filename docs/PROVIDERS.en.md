# Provider adapters

[中文](PROVIDERS.md)

## Current registry

Browser extension v0.4 registers:

- global providers: ChatGPT, Gemini, Claude, Perplexity, Microsoft Copilot, Grok, Mistral Le Chat, and Poe;
- Chinese providers: DeepSeek, Kimi, Qwen, Doubao, Tencent Yuanbao, Zhipu Qingyan, ERNIE/Wenxiaoyan, iFlytek Spark, Tiangong AI, and Hailuo AI.

Each adapter declares its provider ID, display name, official page hostnames, start page, composer selectors, explicit send-button selectors, file-import capability, and automatic-send capability. Python and browser registries are validated through server account tests, manifest validation, and JavaScript checks.

## Stability boundary

A web DOM is not a stable API. Semi-automatic mode stops and offers copy fallback when no composer is found. Full automation clicks only when both a known composer and known send button are present; a generic `button[type=submit]` is accepted only inside the composer's own form. Current-chat capture for ChatGPT, Gemini, Claude, and DeepSeek is beta; the other providers are experimental. Failures known not to have sent become `failed`. A possibly clicked send remains `dispatching` or `sent_unconfirmed` for marker recovery or user resolution and is never retried automatically. Three consecutive adapter failures trip a circuit breaker.

Run `contextvault providers` for the current server capability declaration. Adding a provider requires coordinated server metadata, extension hostname/selectors, minimum manifest host permission, and login/composer/send/fallback testing.

ContextVault never signs in through unofficial mirrors, stores provider credentials, or reuses one account's authorization for another provider.
