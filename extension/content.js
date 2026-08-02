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

async function stableMessageId(role, content, element, index) {
  const explicit = element.getAttribute("data-message-id") || element.id;
  if (explicit) return explicit;
  const bytes = new TextEncoder().encode(`${role}\0${content}\0${index}`);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest).slice(0, 12), (item) => item.toString(16).padStart(2, "0")).join("");
}

async function captureConversation(provider) {
  const definitions = contextVaultCaptureSelectors(provider);
  const seen = new Set();
  const captured = [];
  for (const definition of definitions) {
    for (const element of document.querySelectorAll(definition.selector)) {
      if (seen.has(element)) continue;
      seen.add(element);
      const role = definition.role || element.getAttribute(definition.roleAttribute || "") || "";
      if (!['user', 'assistant'].includes(role)) continue;
      const content = (element.innerText || element.textContent || "").trim();
      if (!content || content.length > 200000) continue;
      captured.push({ role, content, element });
    }
  }
  const messages = [];
  for (let index = 0; index < captured.length; index += 1) {
    const item = captured[index];
    messages.push({
      id: await stableMessageId(item.role, item.content, item.element, index),
      role: item.role,
      content: item.content,
    });
  }
  return {
    provider,
    conversation_url: location.href,
    title: document.title || "Captured conversation",
    messages,
    maturity: contextVaultProviderMaturity(provider),
  };
}

chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
  const provider = contextVaultProviderForHostname(location.hostname);
  if (request.type === "contextvault:probe") {
    const composer = provider ? composerFor(provider) : null;
    const selectors = provider ? contextVaultCaptureSelectors(provider) : [];
    const captureReady = selectors.some((item) => document.querySelector(item.selector));
    sendResponse({ provider, ready: Boolean(composer), captureReady, maturity: provider ? contextVaultProviderMaturity(provider) : null, hostname: location.hostname });
    return;
  }
  if (request.type === "contextvault:capture") {
    if (!provider) {
      sendResponse({ ok: false, error: "当前页面不属于受支持的服务商。" });
      return;
    }
    captureConversation(provider)
      .then((result) => sendResponse({ ok: true, ...result }))
      .catch((error) => sendResponse({ ok: false, error: error.message }));
    return true;
  }
  if (request.type === "contextvault:hasMarker") {
    const marker = String(request.marker || "");
    sendResponse({ found: Boolean(marker) && (document.body.innerText || "").includes(marker) });
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
