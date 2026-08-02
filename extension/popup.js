const PROTOCOL_VERSION = 2;
const state = { base: "", token: "", tab: null, provider: null, routes: [], preview: null, receiptId: null, clientId: null };
const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const response = await fetch(`${state.base}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-ContextVault-Token": state.token,
      "X-ContextVault-Protocol": String(PROTOCOL_VERSION),
      ...(options.headers || {}),
    },
  });
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || "本地 ContextVault 请求失败");
  return body;
}

function message(text, error = false) {
  $("message").textContent = text;
  $("message").style.color = error ? "#9c3c3c" : "#155438";
}

function selectedRoute() {
  return state.routes.find((item) => item.id === $("route-select").value);
}

async function connect() {
  state.base = $("api-base").value.trim().replace(/\/$/, "");
  state.token = $("pairing-token").value.trim();
  if (!/^http:\/\/(127\.0\.0\.1|localhost):\d+$/.test(state.base)) throw new Error("只允许连接本机 HTTP 服务");
  if (!state.token) throw new Error("请输入配对 Token");
  await chrome.storage.local.set({ base: state.base, token: state.token });
  const version = await api("/api/version");
  if (PROTOCOL_VERSION < version.minimum_protocol_version || PROTOCOL_VERSION > version.protocol_version) {
    throw new Error(`扩展协议 ${PROTOCOL_VERSION} 与本地服务协议 ${version.protocol_version} 不兼容，请升级较旧的一端。`);
  }
  const stored = await chrome.storage.local.get(["clientId"]);
  state.clientId = stored.clientId || crypto.randomUUID();
  await chrome.storage.local.set({ clientId: state.clientId });
  await api("/api/clients/register", {
    method: "POST",
    body: JSON.stringify({
      id: state.clientId,
      client_type: "chrome-extension",
      client_version: chrome.runtime.getManifest().version,
      protocol_version: PROTOCOL_VERSION,
    }),
  });
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  state.tab = tab;
  const hostname = new URL(tab.url).hostname;
  state.provider = contextVaultProviderForHostname(hostname);
  if (!state.provider) throw new Error("请在受支持的 AI 对话页面打开扩展");
  const probe = await chrome.tabs.sendMessage(tab.id, { type: "contextvault:probe" });
  $("page-status").textContent = probe.ready
    ? `已识别 ${state.provider}，登录态输入框可用`
    : `已识别 ${state.provider}，但未找到输入框；请先登录并打开对话`;
  const { items } = await api("/api/routes");
  state.routes = items.filter((item) => item.target_platform === state.provider && item.enabled);
  const select = $("route-select");
  select.replaceChildren();
  state.routes.forEach((route) => {
    const option = document.createElement("option");
    option.value = route.id;
    option.textContent = `${route.space_name} → ${route.target_label}`;
    select.append(option);
  });
  if (!state.routes.length) throw new Error(`没有指向当前 ${state.provider} 页面的启用路线`);
  updateAccountLabel();
  $("setup").hidden = true;
  $("workflow").hidden = false;
  message("本地服务已连接");
}

function updateAccountLabel() {
  const route = selectedRoute();
  $("account-confirm-label").textContent = route
    ? `我确认当前登录的是目标账号“${route.target_label}”`
    : "我确认当前登录账号正确";
  $("account-confirm").checked = false;
  $("inject").disabled = true;
}

async function preview() {
  const route = selectedRoute();
  if (!route) throw new Error("请选择同步路线");
  const approved = $("sensitive-confirm").checked;
  const { item } = await api(`/api/routes/${route.id}/preview`, {
    method: "POST",
    body: JSON.stringify({ approve_sensitive: approved }),
  });
  state.preview = item;
  $("preview-content").value = item.content;
  $("policy-result").textContent = `包含 ${item.included.length} 条资料、${item.attachments.length} 个附件引用；阻止 ${item.blocked.length} 条；待本次确认 ${item.awaiting_confirmation.length} 条。`;
  $("copy").disabled = false;
  $("inject").disabled = !$("account-confirm").checked || item.awaiting_confirmation.length > 0;
  message(item.awaiting_confirmation.length ? "仍有 ask 字段未确认" : "预览已生成，请检查最终内容", item.awaiting_confirmation.length > 0);
}

async function prepareAndInject() {
  if (!state.preview || !$("account-confirm").checked) throw new Error("请先预览并确认目标账号");
  const route = selectedRoute();
  const { item } = await api(`/api/routes/${route.id}/sync`, {
    method: "POST",
    body: JSON.stringify({ approve_sensitive: $("sensitive-confirm").checked }),
  });
  const response = await chrome.tabs.sendMessage(state.tab.id, {
    type: "contextvault:inject",
    content: item.content,
  });
  if (!response?.ok) throw new Error(response?.error || "页面填入失败");
  state.receiptId = item.id;
  $("acknowledge").disabled = false;
  message("内容已填入，但尚未发送。请在页面检查并自行发送。", false);
}

async function acknowledge() {
  if (!state.receiptId) throw new Error("没有待确认的同步回执");
  await api(`/api/receipts/${state.receiptId}/acknowledge`, { method: "POST", body: "{}" });
  $("acknowledge").disabled = true;
  message("已记录为完成。ContextVault 现在会把该版本用于后续 diff。");
}

async function configureAutomation(enabled) {
  const route = selectedRoute();
  if (!route) throw new Error("请选择同步路线");
  const risk = $("automation-risk").checked;
  if (enabled && !risk) throw new Error("开启全自动前必须阅读并勾选数据安全风险提示");
  const interval = Number($("automation-interval").value);
  const { item } = await api(`/api/routes/${route.id}/automation`, {
    method: "POST",
    body: JSON.stringify({ enabled, interval_minutes: interval, risk_acknowledged: risk }),
  });
  message(enabled ? `全自动已开启，最短间隔 ${item.interval_minutes} 分钟` : "全自动已关闭");
}

async function run(action) {
  try { await action(); } catch (error) { message(error.message, true); }
}

$("save-settings").addEventListener("click", () => run(connect));
$("route-select").addEventListener("change", updateAccountLabel);
$("account-confirm").addEventListener("change", () => {
  $("inject").disabled = !state.preview || !$("account-confirm").checked || state.preview.awaiting_confirmation.length > 0;
});
$("sensitive-confirm").addEventListener("change", () => { state.preview = null; $("inject").disabled = true; });
$("preview").addEventListener("click", () => run(preview));
$("inject").addEventListener("click", () => run(prepareAndInject));
$("acknowledge").addEventListener("click", () => run(acknowledge));
$("enable-automation").addEventListener("click", () => run(() => configureAutomation(true)));
$("disable-automation").addEventListener("click", () => run(() => configureAutomation(false)));
$("copy").addEventListener("click", () => run(async () => {
  await navigator.clipboard.writeText($("preview-content").value);
  message("预览已复制到剪贴板");
}));

chrome.storage.local.get(["base", "token"]).then((saved) => {
  if (saved.base) $("api-base").value = saved.base;
  if (saved.token) $("pairing-token").value = saved.token;
  if (saved.base && saved.token) run(connect);
});
