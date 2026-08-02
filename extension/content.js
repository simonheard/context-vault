const PROVIDERS = {
  "chatgpt.com": "chatgpt",
  "chat.openai.com": "chatgpt",
  "gemini.google.com": "gemini",
  "claude.ai": "claude",
};

function composerFor(provider) {
  const selectors = {
    chatgpt: ["#prompt-textarea", "textarea[data-testid='prompt-textarea']", "div[contenteditable='true']"],
    gemini: ["rich-textarea .ql-editor", "div[contenteditable='true']", "textarea"],
    claude: ["div[contenteditable='true']", "textarea"],
  };
  for (const selector of selectors[provider] || []) {
    const element = document.querySelector(selector);
    if (element && element.offsetParent !== null) return element;
  }
  return null;
}

function fillComposer(element, text) {
  element.focus();
  if (element instanceof HTMLTextAreaElement || element instanceof HTMLInputElement) {
    const prototype = element instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(prototype, "value")?.set;
    if (setter) setter.call(element, text);
    else element.value = text;
    element.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: text }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
    return;
  }
  const selection = window.getSelection();
  const range = document.createRange();
  range.selectNodeContents(element);
  selection.removeAllRanges();
  selection.addRange(range);
  const inserted = document.execCommand("insertText", false, text);
  if (!inserted) {
    element.textContent = text;
    element.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: text }));
  }
}

chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
  const provider = PROVIDERS[location.hostname];
  if (request.type === "contextvault:probe") {
    const composer = provider ? composerFor(provider) : null;
    sendResponse({ provider, ready: Boolean(composer), hostname: location.hostname });
    return;
  }
  if (request.type === "contextvault:inject") {
    const composer = provider ? composerFor(provider) : null;
    if (!composer) {
      sendResponse({ ok: false, error: "未找到输入框。请确认已登录并打开一个新对话。" });
      return;
    }
    try {
      fillComposer(composer, String(request.content || ""));
      sendResponse({ ok: true, provider });
    } catch (error) {
      sendResponse({ ok: false, error: error.message });
    }
  }
});
