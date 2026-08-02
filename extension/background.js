importScripts("providers.js");

const PROTOCOL_VERSION = 2;
let automationRunning = false;

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

async function providerTab(providerId) {
  const provider = CONTEXTVAULT_PROVIDERS[providerId];
  if (!provider) throw new Error(`Unsupported provider: ${providerId}`);
  const tabs = await chrome.tabs.query({});
  let tab = tabs.find((item) => {
    try { return provider.hosts.includes(new URL(item.url).hostname); } catch { return false; }
  });
  if (!tab) tab = await chrome.tabs.create({ url: provider.startUrl, active: false });
  await waitUntilComplete(tab.id);
  return tab;
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

async function notify(title, message) {
  await chrome.notifications.create({
    type: "basic",
    iconUrl: "icon.svg",
    title,
    message,
  }).catch(() => undefined);
}

async function executeJob(job) {
  const tab = await providerTab(job.target_platform);
  const probe = await chrome.tabs.sendMessage(tab.id, { type: "contextvault:probe" });
  if (!probe?.ready) throw new Error(`${job.target_label} 页面未登录或没有可用输入框`);
  const prepared = await api(`/api/routes/${job.route_id}/automate`, {
    method: "POST",
    body: "{}",
  });
  try {
    const response = await chrome.tabs.sendMessage(tab.id, {
      type: "contextvault:autoSend",
      content: prepared.item.content,
    });
    if (!response?.sent) throw new Error(response?.error || "自动发送按钮不可用");
    await api(`/api/receipts/${prepared.item.id}/acknowledge`, {
      method: "POST",
      body: "{}",
    });
  } catch (error) {
    await api(`/api/receipts/${prepared.item.id}/fail`, {
      method: "POST",
      body: JSON.stringify({ reason: error.message }),
    }).catch(() => undefined);
    throw error;
  }
  await notify("ContextVault 自动同步完成", `${job.target_label}：${job.change_count} 项变化`);
}

async function automationTick() {
  if (automationRunning) return;
  automationRunning = true;
  try {
    if (!await settings()) return;
    const { items } = await api("/api/automation/jobs");
    for (const job of items) {
      try {
        await executeJob(job);
      } catch (error) {
        await notify("ContextVault 自动同步暂停", `${job.target_label}：${error.message}`);
      }
    }
  } catch (error) {
    await notify("ContextVault 自动同步不可用", error.message);
  } finally {
    automationRunning = false;
  }
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create("contextvault-automation", { periodInMinutes: 5 });
});
chrome.runtime.onStartup.addListener(() => {
  chrome.alarms.create("contextvault-automation", { periodInMinutes: 5 });
});
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "contextvault-automation") automationTick();
});
