function composerFor(provider) {
  for (const selector of CONTEXTVAULT_PROVIDERS[provider]?.composers || []) {
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

function sendButtonFor(provider, composer) {
  for (const selector of CONTEXTVAULT_PROVIDERS[provider]?.send || []) {
    const scope = selector.includes("type='submit'") ? composer.closest("form") : document;
    if (!scope) continue;
    const element = scope.querySelector(selector);
    if (element && element.offsetParent !== null && !element.disabled) return element;
  }
  return null;
}

chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
  const provider = contextVaultProviderForHostname(location.hostname);
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
  if (request.type === "contextvault:autoSend") {
    const composer = provider ? composerFor(provider) : null;
    if (!composer) {
      sendResponse({ sent: false, error: "未找到输入框；请检查登录状态。" });
      return;
    }
    try {
      fillComposer(composer, String(request.content || ""));
      window.setTimeout(() => {
        const button = sendButtonFor(provider, composer);
        if (!button) {
          sendResponse({ sent: false, error: "未找到明确的发送按钮；已安全停止。" });
          return;
        }
        button.click();
        sendResponse({ sent: true, provider });
      }, 800);
      return true;
    } catch (error) {
      sendResponse({ sent: false, error: error.message });
    }
  }
});
