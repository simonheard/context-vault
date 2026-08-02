const CONTEXTVAULT_PROVIDERS = {
  chatgpt: { name: "ChatGPT", hosts: ["chatgpt.com", "chat.openai.com"], startUrl: "https://chatgpt.com/", composers: ["#prompt-textarea", "textarea[data-testid='prompt-textarea']", "div[contenteditable='true']"], send: ["button[data-testid='send-button']", "button[aria-label*='Send']"] },
  gemini: { name: "Gemini", hosts: ["gemini.google.com"], startUrl: "https://gemini.google.com/app", composers: ["rich-textarea .ql-editor", "div[contenteditable='true']", "textarea"], send: ["button.send-button", "button[aria-label*='Send']"] },
  claude: { name: "Claude", hosts: ["claude.ai"], startUrl: "https://claude.ai/new", composers: ["div[contenteditable='true']", "textarea"], send: ["button[aria-label*='Send']", "button[type='submit']"] },
  perplexity: { name: "Perplexity", hosts: ["www.perplexity.ai", "perplexity.ai"], startUrl: "https://www.perplexity.ai/", composers: ["textarea", "div[contenteditable='true']"], send: ["button[aria-label*='Submit']", "button[aria-label*='Send']"] },
  copilot: { name: "Microsoft Copilot", hosts: ["copilot.microsoft.com"], startUrl: "https://copilot.microsoft.com/", composers: ["textarea", "div[contenteditable='true']"], send: ["button[aria-label*='Submit']", "button[aria-label*='Send']"] },
  grok: { name: "Grok", hosts: ["grok.com"], startUrl: "https://grok.com/", composers: ["textarea", "div[contenteditable='true']"], send: ["button[type='submit']", "button[aria-label*='Send']"] },
  mistral: { name: "Le Chat", hosts: ["chat.mistral.ai"], startUrl: "https://chat.mistral.ai/chat", composers: ["textarea", "div[contenteditable='true']"], send: ["button[type='submit']", "button[aria-label*='Send']"] },
  poe: { name: "Poe", hosts: ["poe.com"], startUrl: "https://poe.com/", composers: ["textarea", "div[contenteditable='true']"], send: ["button[type='submit']", "button[aria-label*='Send']"] },
  deepseek: { name: "DeepSeek", hosts: ["chat.deepseek.com"], startUrl: "https://chat.deepseek.com/", composers: ["textarea", "div[contenteditable='true']"], send: ["div[role='button'][aria-label*='发送']", "button[aria-label*='Send']", "button[type='submit']"] },
  kimi: { name: "Kimi", hosts: ["www.kimi.com", "kimi.com", "kimi.moonshot.cn"], startUrl: "https://www.kimi.com/", composers: ["div[contenteditable='true']", "textarea"], send: ["button[aria-label*='发送']", "button[type='submit']"] },
  qwen: { name: "通义千问 / Qwen", hosts: ["www.qianwen.com", "qianwen.com", "tongyi.aliyun.com", "chat.qwen.ai"], startUrl: "https://www.qianwen.com/", composers: ["textarea", "div[contenteditable='true']"], send: ["button[aria-label*='发送']", "button[type='submit']"] },
  doubao: { name: "豆包", hosts: ["www.doubao.com", "doubao.com"], startUrl: "https://www.doubao.com/chat/", composers: ["textarea", "div[contenteditable='true']"], send: ["button[aria-label*='发送']", "button[type='submit']"] },
  yuanbao: { name: "腾讯元宝", hosts: ["yuanbao.tencent.com", "ai.tencent.com"], startUrl: "https://yuanbao.tencent.com/", composers: ["textarea", "div[contenteditable='true']"], send: ["button[aria-label*='发送']", "button[type='submit']"] },
  zhipu: { name: "智谱清言", hosts: ["chatglm.cn", "www.chatglm.cn"], startUrl: "https://chatglm.cn/", composers: ["textarea", "div[contenteditable='true']"], send: ["button[aria-label*='发送']", "button[type='submit']"] },
  ernie: { name: "文心一言 / 文小言", hosts: ["yiyan.baidu.com", "chat.baidu.com"], startUrl: "https://yiyan.baidu.com/", composers: ["textarea", "div[contenteditable='true']"], send: ["button[aria-label*='发送']", "button[type='submit']"] },
  spark: { name: "讯飞星火", hosts: ["xinghuo.xfyun.cn"], startUrl: "https://xinghuo.xfyun.cn/", composers: ["textarea", "div[contenteditable='true']"], send: ["button[aria-label*='发送']", "button[type='submit']"] },
  tiangong: { name: "天工 AI", hosts: ["www.tiangong.cn", "tiangong.cn"], startUrl: "https://www.tiangong.cn/", composers: ["textarea", "div[contenteditable='true']"], send: ["button[aria-label*='发送']", "button[type='submit']"] },
  hailuo: { name: "海螺 AI", hosts: ["hailuoai.com", "www.hailuoai.com"], startUrl: "https://hailuoai.com/", composers: ["textarea", "div[contenteditable='true']"], send: ["button[aria-label*='发送']", "button[type='submit']"] },
};

function contextVaultProviderForHostname(hostname) {
  return Object.entries(CONTEXTVAULT_PROVIDERS).find(([, item]) => item.hosts.includes(hostname))?.[0] || null;
}
