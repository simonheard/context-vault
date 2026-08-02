importScripts("providers.js");

const PROTOCOL_VERSION = 3;
const LOCK_KEY = "automationLock";
const KNOWLEDGE_PROBE_PROMPT = `请根据你当前账号中可用的记忆和个性化信息，总结你已经知道的关于我的事实。不要猜测，不要输出密码、令牌、身份证号或精确地址。为了便于我导出，请只使用以下第一人称句式，每行一条；不知道的类别不要写：\nMy name is ...\nI live in ...\nI work at ...\nI study at ...\nI speak ...\nI prefer ...\nI use ...`;

async function settings() {
  const saved = await chrome.storage.local.get(["base", "token"]);
  if (!saved.base || !saved.token) return null;
  return { base: saved.base.replace(/\/$/, ""), token: saved.token };
}

async function api(path, options = {}) {
  const configured = await settings();
  if (!configured) throw new Error("ContextVault extension is not paired");
  const response = await fetch(`${configured.base}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-ContextVault-Token": configured.token,
      "X-ContextVault-Protocol": String(PROTOCOL_VERSION),
      ...(options.headers || {}),
    },
  });
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || "ContextVault automation request failed");
  return body;
}

async function acquireLock() {
  const now = Date.now();
  const saved = await chrome.storage.local.get([LOCK_KEY]);
  if (saved[LOCK_KEY] && now - saved[LOCK_KEY] < 4 * 60 * 1000) return false;
  await chrome.storage.local.set({ [LOCK_KEY]: now });
  return true;
}

async function releaseLock() {
  await chrome.storage.local.remove([LOCK_KEY]);
}

async function providerTab(providerId, preferredUrl = null, createNew = false) {
  const provider = CONTEXTVAULT_PROVIDERS[providerId];
  if (!provider) throw new Error(`Unsupported provider: ${providerId}`);
  const tabs = await chrome.tabs.query({});
  let tab = null;
  if (preferredUrl) {
    tab = tabs.find((item) => item.url === preferredUrl) || null;
    if (!tab) tab = await chrome.tabs.create({ url: preferredUrl, active: false });
  } else if (!createNew) {
    tab = tabs.find((item) => {
      try { return provider.hosts.includes(new URL(item.url).hostname); } catch { return false; }
    }) || null;
  }
  if (!tab) tab = await chrome.tabs.create({ url: provider.startUrl, active: false });
  await waitUntilComplete(tab.id);
  return await chrome.tabs.get(tab.id);
}

async function waitUntilComplete(tabId) {
  const current = await chrome.tabs.get(tabId);
  if (current.status === "complete") return;
  await new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      chrome.tabs.onUpdated.removeListener(listener);
      reject(new Error("Provider page load timed out"));
    }, 45000);
    function listener(updatedId, info) {
      if (updatedId === tabId && info.status === "complete") {
        clearTimeout(timeout);
        chrome.tabs.onUpdated.removeListener(listener);
        resolve();
      }
    }
    chrome.tabs.onUpdated.addListener(listener);
  });
}

async function waitForConversationUrl(tabId, providerId) {
  const start = CONTEXTVAULT_PROVIDERS[providerId].startUrl;
  for (let attempt = 0; attempt < 20; attempt += 1) {
    const tab = await chrome.tabs.get(tabId);
    if (tab.url && tab.url !== start && !tab.url.endsWith("/new")) return tab.url;
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  return null;
}

async function notify(title, message) {
  await chrome.notifications.create({ type: "basic", iconUrl: "icon.svg", title, message }).catch(() => undefined);
}

async function recoverPendingDispatch() {
  const saved = await chrome.storage.local.get(["pendingDispatch"]);
  const pending = saved.pendingDispatch;
  if (!pending?.receiptId) return;
  const tabs = await chrome.tabs.query({});
  for (const tab of tabs) {
    try {
      const result = await chrome.tabs.sendMessage(tab.id, { type: "contextvault:hasMarker", marker: pending.receiptId });
      if (!result?.found) continue;
      await api(`/api/receipts/${pending.receiptId}/attempted`, { method: "POST", body: "{}" });
      await api(`/api/receipts/${pending.receiptId}/acknowledge`, { method: "POST", body: "{}" });
      await chrome.storage.local.remove(["pendingDispatch"]);
      await notify("ContextVault 已恢复同步状态", "检测到已发送标记，回执已安全完成。");
      return;
    } catch { /* the tab may not host a current content script */ }
  }
  await notify("ContextVault 需要确认", `回执 ${pending.receiptId} 的发送结果未知；不会自动重试。`);
}

async function waitForKnowledgeProbe(tabId) {
  let previous = "";
  let stableCount = 0;
  for (let attempt = 0; attempt < 45; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 2000));
    const capture = await chrome.tabs.sendMessage(tabId, { type: "contextvault:capture" });
    const assistant = capture?.messages?.filter((item) => item.role === "assistant") || [];
    const latest = assistant.at(-1)?.content || "";
    if (latest && latest === previous) stableCount += 1;
    else stableCount = 0;
    previous = latest;
    if (stableCount >= 2) return capture;
  }
  throw new Error("资料探测对话等待回复超时");
}

function isBlankConversationUrl(providerId, value) {
  try {
    const current = new URL(value);
    const start = new URL(CONTEXTVAULT_PROVIDERS[providerId].startUrl);
    const normalized = current.pathname.replace(/\/$/, "") || "/";
    const startPath = start.pathname.replace(/\/$/, "") || "/";
    return current.hostname === start.hostname && (normalized === startPath || normalized.endsWith("/new"));
  } catch {
    return false;
  }
}

async function captureJob(job) {
  const tab = await providerTab(job.platform, job.conversation_url, false);
  let capture = await chrome.tabs.sendMessage(tab.id, { type: "contextvault:capture" });
  let knowledgeProbe = false;
  if (capture?.ok && !capture.messages?.length && isBlankConversationUrl(job.platform, capture.conversation_url)) {
    const sent = await chrome.tabs.sendMessage(tab.id, { type: "contextvault:autoSend", content: KNOWLEDGE_PROBE_PROMPT });
    if (!sent?.sent) throw new Error(sent?.error || "无法创建资料探测对话");
    knowledgeProbe = true;
    capture = await waitForKnowledgeProbe(tab.id);
  }
  if (!capture?.ok || !capture.messages?.length) {
    throw new Error(capture?.error || `${job.account_label} 当前对话没有可捕获消息；若页面并非空白新对话，请检查页面适配器`);
  }
  const result = await api("/api/captures/ingest", {
    method: "POST",
    body: JSON.stringify({
      account_id: job.account_id,
      provider: job.platform,
      conversation_url: capture.conversation_url,
      title: capture.title,
      messages: capture.messages,
      space: "personal",
      knowledge_probe: knowledgeProbe,
    }),
  });
  if (result.item.candidates) {
    await notify("ContextVault 拉取完成", `${job.account_label}：新增 ${result.item.candidates} 条候选资料`);
  }
}

async function executePushJob(job) {
  const tab = await providerTab(job.target_platform, job.conversation_url, job.create_new_conversation);
  const probe = await chrome.tabs.sendMessage(tab.id, { type: "contextvault:probe" });
  if (!probe?.ready) throw new Error(`${job.target_label} 页面未登录或没有可用输入框`);
  const prepared = await api(`/api/routes/${job.route_id}/automate`, { method: "POST", body: "{}" });
  await api(`/api/receipts/${prepared.item.id}/dispatch`, { method: "POST", body: "{}" });
  await chrome.storage.local.set({ pendingDispatch: { receiptId: prepared.item.id, routeId: job.route_id, startedAt: Date.now() } });

  let response;
  try {
    response = await chrome.tabs.sendMessage(tab.id, {
      type: "contextvault:autoSend",
      content: `${prepared.item.content}\n\n[ContextVault sync ${prepared.item.version} · ${prepared.item.id}]`,
    });
  } catch (error) {
    throw new Error(`发送结果未知，已禁止自动重试：${error.message}`);
  }
  if (!response?.sent) {
    await api(`/api/receipts/${prepared.item.id}/fail`, {
      method: "POST",
      body: JSON.stringify({ reason: response?.error || "自动发送按钮不可用" }),
    });
    await chrome.storage.local.remove(["pendingDispatch"]);
    throw new Error(response?.error || "自动发送按钮不可用");
  }

  await api(`/api/receipts/${prepared.item.id}/attempted`, { method: "POST", body: "{}" });
  const conversationUrl = await waitForConversationUrl(tab.id, job.target_platform);
  if (conversationUrl) {
    await api(`/api/routes/${job.route_id}/binding`, {
      method: "POST",
      body: JSON.stringify({ conversation_url: conversationUrl }),
    }).catch(() => undefined);
  }
  await api(`/api/receipts/${prepared.item.id}/acknowledge`, { method: "POST", body: "{}" });
  await chrome.storage.local.remove(["pendingDispatch"]);
  await notify("ContextVault 自动同步完成", `${job.target_label}：${job.change_count} 项变化`);
}

async function automationTick() {
  if (!await settings() || !await acquireLock()) return;
  try {
    await recoverPendingDispatch();
    const captureResult = await api("/api/capture/jobs");
    for (const job of captureResult.items) {
      try { await captureJob(job); }
      catch (error) {
        await api(`/api/accounts/${job.account_id}/capture-failure`, { method: "POST", body: JSON.stringify({ reason: error.message }) }).catch(() => undefined);
        await notify("ContextVault 自动拉取暂停", `${job.account_label}：${error.message}`);
      }
    }
    const pushResult = await api("/api/automation/jobs");
    for (const job of pushResult.items) {
      try { await executePushJob(job); }
      catch (error) {
        await api(`/api/routes/${job.route_id}/automation-failure`, { method: "POST", body: JSON.stringify({ reason: error.message }) }).catch(() => undefined);
        await notify("ContextVault 自动推送暂停", `${job.target_label}：${error.message}`);
      }
    }
  } catch (error) {
    await notify("ContextVault 自动化不可用", error.message);
  } finally {
    await releaseLock();
  }
}

async function ensureAlarm() {
  const existing = await chrome.alarms.get("contextvault-automation");
  if (!existing) await chrome.alarms.create("contextvault-automation", { periodInMinutes: 5 });
}

chrome.runtime.onInstalled.addListener(ensureAlarm);
chrome.runtime.onStartup.addListener(ensureAlarm);
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "contextvault-automation") automationTick();
});
ensureAlarm();
