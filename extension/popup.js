const PROTOCOL_VERSION = 3;
const state = { mode: null, base: "", token: "", tab: null, provider: null, routes: [], accounts: [], preview: null, receiptId: null, clientId: null };
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
  state.mode = "service";
  state.base = $("api-base").value.trim().replace(/\/$/, "");
  state.token = $("pairing-token").value.trim();
  if (!/^http:\/\/(127\.0\.0\.1|localhost):\d+$/.test(state.base)) throw new Error("只允许连接本机 HTTP 服务");
  if (!state.token) throw new Error("请输入配对 Token");
  await chrome.storage.local.set({ mode: "service", base: state.base, token: state.token });
  const version = await api("/api/version");
  if (PROTOCOL_VERSION < version.minimum_protocol_version || PROTOCOL_VERSION > version.protocol_version) {
    throw new Error(`扩展协议 ${PROTOCOL_VERSION} 与本地服务协议 ${version.protocol_version} 不兼容，请升级较旧的一端。`);
  }
  const stored = await chrome.storage.local.get(["clientId"]);
  state.clientId = stored.clientId || crypto.randomUUID();
  await chrome.storage.local.set({ clientId: state.clientId });
  const registration = await api("/api/clients/register", {
    method: "POST",
    body: JSON.stringify({
      id: state.clientId,
      client_type: "chrome-extension",
      client_version: chrome.runtime.getManifest().version,
      protocol_version: PROTOCOL_VERSION,
    }),
  });
  if (registration.item.client_token) {
    state.token = registration.item.client_token;
    $("pairing-token").value = state.token;
    await chrome.storage.local.set({ token: state.token });
  }
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  state.tab = tab;
  const hostname = new URL(tab.url).hostname;
  state.provider = contextVaultProviderForHostname(hostname);
  if (!state.provider) throw new Error("请在受支持的 AI 对话页面打开扩展");
  const probe = await chrome.tabs.sendMessage(tab.id, { type: "contextvault:probe" });
  $("page-status").textContent = probe.ready
    ? `已识别 ${state.provider}（${probe.maturity || "experimental"}），输入框可用${probe.captureReady ? "，可拉取当前对话" : ""}`
    : `已识别 ${state.provider}，但未找到输入框；请先登录并打开对话`;
  const [{ items }, accountResult] = await Promise.all([api("/api/routes"), api("/api/accounts")]);
  state.routes = items.filter((item) => item.target_platform === state.provider && item.enabled);
  state.accounts = accountResult.items.filter((item) => item.platform === state.provider && item.status === "active");
  const select = $("route-select");
  select.replaceChildren();
  state.routes.forEach((route) => {
    const option = document.createElement("option");
    option.value = route.id;
    option.textContent = `${route.space_name} → ${route.target_label}`;
    select.append(option);
  });
  if (!state.routes.length) {
    const option = document.createElement("option");
    option.textContent = `没有指向当前 ${state.provider} 页面的路线`;
    option.value = "";
    select.append(option);
    $("preview").disabled = true;
  }
  const captureSelect = $("capture-account");
  captureSelect.replaceChildren();
  state.accounts.forEach((account) => {
    const option = document.createElement("option");
    option.value = account.id;
    option.textContent = account.account_label;
    captureSelect.append(option);
  });
  if (!state.accounts.length) {
    const option = document.createElement("option");
    option.textContent = `请先在后台添加 ${state.provider} 账号`;
    option.value = "";
    captureSelect.append(option);
    $("capture-now").disabled = true;
    $("enable-capture").disabled = true;
  }
  updateAccountLabel();
  $("setup").hidden = true;
  $("workflow").hidden = false;
  message("本地服务已连接");
}

async function startStandalone() {
  state.mode = "standalone";
  await chrome.storage.local.set({ mode: "standalone" });
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  state.tab = tab;
  state.provider = contextVaultProviderForHostname(new URL(tab.url).hostname);
  if (!state.provider) throw new Error("请在受支持的 AI 对话页面打开扩展");
  const probe = await chrome.tabs.sendMessage(tab.id, { type: "contextvault:probe" });
  $("page-status").textContent = `${CONTEXTVAULT_PROVIDERS[state.provider].name} · 独立插件模式 · ${probe.maturity || "experimental"}`;
  state.routes = [{ id: `standalone:${state.provider}`, target_platform: state.provider, target_label: CONTEXTVAULT_PROVIDERS[state.provider].name, space_name: "browser", enabled: 1 }];
  state.accounts = [{ id: `standalone:${state.provider}`, platform: state.provider, account_label: `${CONTEXTVAULT_PROVIDERS[state.provider].name}（当前 Chrome Profile）`, status: "active" }];
  const routeSelect = $("route-select");
  routeSelect.replaceChildren();
  const routeOption = document.createElement("option"); routeOption.value = state.routes[0].id; routeOption.textContent = `浏览器资料库 → ${state.routes[0].target_label}`; routeSelect.append(routeOption);
  const captureSelect = $("capture-account");
  captureSelect.replaceChildren();
  const accountOption = document.createElement("option"); accountOption.value = state.accounts[0].id; accountOption.textContent = state.accounts[0].account_label; captureSelect.append(accountOption);
  $("preview").disabled = false; $("capture-now").disabled = false; $("enable-capture").disabled = false;
  updateAccountLabel();
  $("setup").hidden = true; $("workflow").hidden = false;
  message("独立插件资料库已启用；不需要 CLI 或本地服务");
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
  if (state.mode === "standalone") {
    const vault = await contextVaultStandaloneLoad();
    const profile = contextVaultStandaloneProfile(vault, $("sensitive-confirm").checked);
    state.preview = { content: profile.content, included: profile.claims, attachments: [], blocked: [], awaiting_confirmation: [] };
    $("preview-content").value = profile.content;
    $("policy-result").textContent = `包含 ${profile.claims.length} 条已确认资料；待审阅候选不会发送。`;
    $("copy").disabled = false;
    $("inject").disabled = !$("account-confirm").checked || !profile.claims.length;
    message(profile.claims.length ? "独立资料预览已生成" : "资料库还没有已确认资料，请先拉取并在管理页确认", !profile.claims.length);
    return;
  }
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
  if (state.mode === "standalone") {
    const response = await chrome.tabs.sendMessage(state.tab.id, { type: "contextvault:inject", content: state.preview.content });
    if (!response?.ok) throw new Error(response?.error || "页面填入失败");
    state.receiptId = crypto.randomUUID();
    const vault = await contextVaultStandaloneLoad();
    vault.receipts.push({ id: state.receiptId, provider: state.provider, status: "prepared", contentHash: await contextVaultStandaloneDigest(state.preview.content), createdAt: new Date().toISOString() });
    await contextVaultStandaloneSave(vault);
    $("acknowledge").disabled = false;
    message("内容已填入，请检查并自行发送");
    return;
  }
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
  if (state.mode === "standalone") {
    const vault = await contextVaultStandaloneLoad();
    const receipt = vault.receipts.find((item) => item.id === state.receiptId);
    if (receipt) { receipt.status = "completed"; receipt.completedAt = new Date().toISOString(); }
    await contextVaultStandaloneSave(vault);
    $("acknowledge").disabled = true; message("独立模式回执已记录"); return;
  }
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
  if (state.mode === "standalone") {
    const item = await contextVaultStandaloneConfigure("route", state.provider, { enabled, intervalMinutes: interval, conversationUrl: state.tab.url });
    message(enabled ? `独立全自动已开启，每 ${item.intervalMinutes} 分钟检查资料变化` : "独立全自动已关闭"); return;
  }
  const { item } = await api(`/api/routes/${route.id}/automation`, {
    method: "POST",
    body: JSON.stringify({ enabled, interval_minutes: interval, risk_acknowledged: risk }),
  });
  message(enabled ? `全自动已开启，最短间隔 ${item.interval_minutes} 分钟` : "全自动已关闭");
}

async function captureNow() {
  const accountId = $("capture-account").value;
  if (!accountId) throw new Error("请选择当前网页对应的来源账号");
  if (state.mode === "standalone") {
    message("正在后台拉取；空白新对话会自动发起资料探测，请稍候…");
    const result = await chrome.runtime.sendMessage({ type: "contextvault:standaloneCaptureNow", provider: state.provider, conversationUrl: state.tab.url });
    if (!result?.ok) throw new Error(result?.error || "独立拉取失败");
    const vault = await contextVaultStandaloneLoad();
    const pending = vault.claims.filter((item) => item.status === "pending").length;
    message(`拉取完成，当前有 ${pending} 条候选待审阅。`); return;
  }
  const capture = await chrome.tabs.sendMessage(state.tab.id, { type: "contextvault:capture" });
  if (!capture?.ok || !capture.messages?.length) throw new Error(capture?.error || "当前页面没有可拉取的对话消息");
  const { item } = await api("/api/captures/ingest", {
    method: "POST",
    body: JSON.stringify({ account_id: accountId, provider: state.provider, conversation_url: capture.conversation_url, title: capture.title, messages: capture.messages, space: "personal" }),
  });
  message(`已拉取 ${item.messages} 条消息，新增 ${item.candidates} 条候选，发现 ${item.conflicts} 个冲突。`);
}

async function configureCapture(enabled) {
  const accountId = $("capture-account").value;
  if (!accountId) throw new Error("请选择来源账号");
  const risk = $("capture-risk").checked;
  if (enabled && !risk) throw new Error("开启自动拉取前必须阅读并确认隐私风险");
  if (state.mode === "standalone") {
    const item = await contextVaultStandaloneConfigure("capture", state.provider, { enabled, intervalMinutes: Number($("capture-interval").value), conversationUrl: state.tab.url });
    message(enabled ? `独立自动拉取已开启，每 ${item.intervalMinutes} 分钟检查一次` : "独立自动拉取已关闭"); return;
  }
  const { item } = await api(`/api/accounts/${accountId}/capture`, {
    method: "POST",
    body: JSON.stringify({ enabled, interval_minutes: Number($("capture-interval").value), risk_acknowledged: risk, conversation_url: state.tab.url }),
  });
  message(enabled ? `自动拉取已开启，每 ${item.interval_minutes} 分钟检查一次` : "自动拉取已关闭");
}

async function createNewConversation() {
  const provider = CONTEXTVAULT_PROVIDERS[state.provider];
  state.tab = await chrome.tabs.create({ url: provider.startUrl, active: true });
  message("已创建新的服务商页面；登录后可将它作为专用同步对话。");
}

async function run(action) {
  try { await action(); } catch (error) { message(error.message, true); }
}

$("save-settings").addEventListener("click", () => run(connect));
$("start-standalone").addEventListener("click", () => run(startStandalone));
$("open-vault").addEventListener("click", () => chrome.runtime.openOptionsPage());
$("switch-mode").addEventListener("click", async () => { await chrome.storage.local.remove(["mode"]); $("workflow").hidden = true; $("setup").hidden = false; message("请选择运行模式"); });
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
$("capture-now").addEventListener("click", () => run(captureNow));
$("enable-capture").addEventListener("click", () => run(() => configureCapture(true)));
$("disable-capture").addEventListener("click", () => run(() => configureCapture(false)));
$("new-conversation").addEventListener("click", () => run(createNewConversation));
$("copy").addEventListener("click", () => run(async () => {
  await navigator.clipboard.writeText($("preview-content").value);
  message("预览已复制到剪贴板");
}));

chrome.storage.local.get(["mode", "base", "token"]).then((saved) => {
  if (saved.base) $("api-base").value = saved.base;
  if (saved.token) $("pairing-token").value = saved.token;
  if (saved.mode === "standalone") run(startStandalone);
  else if (saved.mode === "service" && saved.base && saved.token) run(connect);
});
