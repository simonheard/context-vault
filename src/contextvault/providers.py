from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional


@dataclass(frozen=True)
class ProviderCapability:
    id: str
    display_name: str
    hostnames: tuple[str, ...]
    start_url: str
    region: str = "global"
    page_injection: bool = True
    automatic_send: bool = True
    file_import: bool = False
    attachment_transfer: bool = False
    notes: str = "Uses the user's logged-in browser session."


def _provider(
    provider_id: str,
    name: str,
    hostnames: tuple[str, ...],
    start_url: str,
    *,
    region: str = "global",
    file_import: bool = False,
    automatic_send: bool = True,
) -> ProviderCapability:
    return ProviderCapability(
        id=provider_id,
        display_name=name,
        hostnames=hostnames,
        start_url=start_url,
        region=region,
        file_import=file_import,
        automatic_send=automatic_send,
    )


PROVIDERS = {
    item.id: item
    for item in (
        _provider("chatgpt", "ChatGPT", ("chatgpt.com", "chat.openai.com"), "https://chatgpt.com/", file_import=True),
        _provider("gemini", "Gemini", ("gemini.google.com",), "https://gemini.google.com/app"),
        _provider("claude", "Claude", ("claude.ai",), "https://claude.ai/new"),
        _provider("perplexity", "Perplexity", ("www.perplexity.ai", "perplexity.ai"), "https://www.perplexity.ai/"),
        _provider("copilot", "Microsoft Copilot", ("copilot.microsoft.com",), "https://copilot.microsoft.com/"),
        _provider("grok", "Grok", ("grok.com",), "https://grok.com/"),
        _provider("mistral", "Le Chat", ("chat.mistral.ai",), "https://chat.mistral.ai/chat"),
        _provider("poe", "Poe", ("poe.com",), "https://poe.com/"),
        _provider("deepseek", "DeepSeek", ("chat.deepseek.com",), "https://chat.deepseek.com/", region="china"),
        _provider("kimi", "Kimi", ("www.kimi.com", "kimi.com", "kimi.moonshot.cn"), "https://www.kimi.com/", region="china"),
        _provider("qwen", "通义千问 / Qwen", ("www.qianwen.com", "qianwen.com", "tongyi.aliyun.com", "chat.qwen.ai"), "https://www.qianwen.com/", region="china"),
        _provider("doubao", "豆包", ("www.doubao.com", "doubao.com"), "https://www.doubao.com/chat/", region="china"),
        _provider("yuanbao", "腾讯元宝", ("yuanbao.tencent.com", "ai.tencent.com"), "https://yuanbao.tencent.com/", region="china"),
        _provider("zhipu", "智谱清言", ("chatglm.cn", "www.chatglm.cn"), "https://chatglm.cn/", region="china"),
        _provider("ernie", "文心一言 / 文小言", ("yiyan.baidu.com", "chat.baidu.com"), "https://yiyan.baidu.com/", region="china"),
        _provider("spark", "讯飞星火", ("xinghuo.xfyun.cn",), "https://xinghuo.xfyun.cn/", region="china"),
        _provider("tiangong", "天工 AI", ("www.tiangong.cn", "tiangong.cn"), "https://www.tiangong.cn/", region="china"),
        _provider("hailuo", "海螺 AI", ("hailuoai.com", "www.hailuoai.com"), "https://hailuoai.com/", region="china"),
    )
}


def provider_capabilities() -> list[dict[str, object]]:
    return [asdict(item) for item in PROVIDERS.values()]


def provider_for_hostname(hostname: str) -> Optional[ProviderCapability]:
    hostname = hostname.lower()
    return next(
        (item for item in PROVIDERS.values() if hostname in item.hostnames), None
    )
