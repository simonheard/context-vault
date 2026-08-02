const titles = {
  overview: "资料总览",
  profile: "用户资料",
  accounts: "AI 账号",
  spaces: "身份空间",
  routes: "同步路线",
  devices: "设备",
  privacy: "隐私与授权",
  history: "同步历史",
};

function showView(name) {
  document.querySelectorAll(".view").forEach((element) => element.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach((element) => element.classList.remove("active"));
  document.getElementById(`${name}-view`).classList.add("active");
  document.querySelector(`[data-view="${name}"]`)?.classList.add("active");
  document.getElementById("page-title").textContent = titles[name];
}

document.querySelectorAll("[data-view]").forEach((button) => {
  button.addEventListener("click", () => showView(button.dataset.view));
});
document.querySelectorAll("[data-view-target]").forEach((button) => {
  button.addEventListener("click", () => showView(button.dataset.viewTarget));
});

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || "请求失败");
  return body;
}

function listItem(title, subtitle, badge) {
  const item = document.createElement("div");
  item.className = "list-item";
  const text = document.createElement("div");
  const strong = document.createElement("strong");
  strong.textContent = title;
  const small = document.createElement("small");
  small.textContent = subtitle;
  const chip = document.createElement("span");
  chip.className = "chip";
  chip.textContent = badge;
  text.append(strong, small);
  item.append(text, chip);
  return item;
}

function emptyMessage(text) {
  const empty = document.createElement("p");
  empty.className = "muted";
  empty.textContent = text;
  return empty;
}

async function loadDashboard() {
  const [{ counts }, health] = await Promise.all([api("/api/dashboard"), api("/api/profile/health")]);
  document.getElementById("metric-claims").textContent = counts.claims;
  document.getElementById("metric-candidates").textContent = counts.candidates;
  document.getElementById("metric-accounts").textContent = counts.accounts;
  document.getElementById("metric-devices").textContent = counts.devices;
  document.getElementById("review-notice").hidden = counts.candidates === 0;
  document.querySelector(".score").textContent = `${health.score}%`;
}

async function loadAccounts() {
  const { items } = await api("/api/accounts");
  const list = document.getElementById("accounts-list");
  const summary = document.getElementById("account-summary");
  list.replaceChildren();
  if (!items.length) {
    list.append(emptyMessage("尚未添加账号。"));
    return;
  }
  items.forEach((item) => list.append(listItem(item.account_label, item.platform, item.status)));
  summary.className = "list";
  summary.replaceChildren(...items.slice(0, 3).map((item) => listItem(item.account_label, item.platform, "未同步")));
  ["route-source", "route-target", "import-account"].forEach((id) => {
    const selector = document.getElementById(id);
    const optional = id !== "route-target";
    selector.replaceChildren();
    if (optional) {
      const blank = document.createElement("option");
      blank.value = "";
      blank.textContent = id === "import-account" ? "不指定账号" : "所有已确认来源";
      selector.append(blank);
    }
    items.forEach((item) => {
      const option = document.createElement("option");
      option.value = item.id;
      option.textContent = `${item.account_label} (${item.platform})`;
      selector.append(option);
    });
  });
}

async function loadSpaces() {
  const { items } = await api("/api/spaces");
  const list = document.getElementById("spaces-list");
  list.replaceChildren(...items.map((item) => listItem(item.display_name, item.name, item.is_default ? "默认" : "隔离")));
  const selector = document.getElementById("claim-space");
  selector.replaceChildren(...items.map((item) => {
    const option = document.createElement("option");
    option.value = item.name;
    option.textContent = item.display_name;
    return option;
  }));
  const routeSelector = document.getElementById("route-space");
  routeSelector.replaceChildren(...items.map((item) => {
    const option = document.createElement("option");
    option.value = item.name;
    option.textContent = item.display_name;
    return option;
  }));
}

async function claimAction(claimId, action) {
  await api(`/api/claims/${claimId}/${action}`, { method: "POST", body: "{}" });
  await Promise.all([loadClaims(), loadDashboard(), loadEvents()]);
}

async function loadClaims() {
  const { items } = await api("/api/claims");
  const list = document.getElementById("claims-list");
  list.replaceChildren();
  if (!items.length) {
    list.append(emptyMessage("暂无资料。手动添加的内容会先进入候选队列。"));
    return;
  }
  items.forEach((item) => {
    const row = listItem(item.attribute, item.value_text, item.status);
    if (item.status === "candidate") {
      const actions = row.querySelector(".chip");
      actions.className = "row-actions";
      actions.replaceChildren();
      const confirm = document.createElement("button");
      confirm.className = "mini-button confirm";
      confirm.textContent = "确认";
      confirm.addEventListener("click", () => claimAction(item.id, "confirm"));
      const reject = document.createElement("button");
      reject.className = "mini-button reject";
      reject.textContent = "拒绝";
      reject.addEventListener("click", () => claimAction(item.id, "reject"));
      actions.append(confirm, reject);
    }
    list.append(row);
  });
}

async function loadEvents() {
  const { items } = await api("/api/events");
  const list = document.getElementById("events-list");
  list.replaceChildren();
  if (!items.length) {
    list.append(emptyMessage("暂无历史记录。"));
    return;
  }
  [...items].reverse().forEach((item) => {
    const time = new Date(item.created_at).toLocaleString();
    list.append(listItem(item.event_type, `${item.aggregate_type} · ${time}`, `#${item.sequence}`));
  });
}

async function loadDevices() {
  const { items } = await api("/api/devices");
  const list = document.getElementById("devices-list");
  list.replaceChildren();
  if (!items.length) {
    list.append(emptyMessage("暂无设备。扫描只会采集白名单元数据。"));
    return;
  }
  items.forEach((item) => {
    const config = item.config;
    list.append(listItem(item.display_name, `${config.os} ${config.os_release} · ${config.architecture}`, `${Object.keys(config.tools || {}).length} tools`));
  });
}

async function previewRoute(routeId, sync = false) {
  try {
    const previewResult = await api(`/api/routes/${routeId}/preview`, { method: "POST", body: "{}" });
    let item = previewResult.item;
    let approveSensitive = false;
    if (item.awaiting_confirmation.length) {
      const approved = window.confirm(`${item.awaiting_confirmation.length} 条私密或敏感资料需要本次确认。是否加入预览？`);
      if (approved) {
        const approvedResult = await api(`/api/routes/${routeId}/preview`, { method: "POST", body: JSON.stringify({ approve_sensitive: true }) });
        item = approvedResult.item;
        approveSensitive = true;
      }
    }
    if (sync) {
      const result = await api(`/api/routes/${routeId}/sync`, { method: "POST", body: JSON.stringify({ approve_sensitive: approveSensitive }) });
      window.alert(`同步包与回执已生成：${result.item.version}`);
    } else {
      window.alert(item.content);
    }
    await Promise.all([loadRoutes(), loadReceipts(), loadEvents()]);
  } catch (error) {
    window.alert(error.message);
  }
}

async function loadRoutes() {
  const { items } = await api("/api/routes");
  const list = document.getElementById("routes-list");
  list.replaceChildren();
  if (!items.length) {
    list.append(emptyMessage("尚未建立同步路线。"));
    return;
  }
  items.forEach((item) => {
    const row = listItem(`${item.source_label || "全部来源"} → ${item.target_label}`, item.space_name, item.enabled ? "启用" : "停用");
    const actions = row.querySelector(".chip");
    actions.className = "row-actions";
    actions.replaceChildren();
    const preview = document.createElement("button");
    preview.className = "mini-button confirm";
    preview.textContent = "预览";
    preview.addEventListener("click", () => previewRoute(item.id));
    const sync = document.createElement("button");
    sync.className = "mini-button";
    sync.textContent = "生成回执";
    sync.addEventListener("click", () => previewRoute(item.id, true));
    actions.append(preview, sync);
    list.append(row);
  });
}

let sensitiveSyncEnabled = false;
async function loadPrivacy() {
  const result = await api("/api/privacy");
  sensitiveSyncEnabled = result.sensitive_sync_enabled;
  document.getElementById("privacy-status").textContent = sensitiveSyncEnabled
    ? "当前开启；每条资料仍受路线级 block / ask / allow 策略约束。"
    : "当前关闭；所有私密和敏感资料都被强制阻止。";
}

async function loadReceipts() {
  const { items } = await api("/api/receipts");
  const list = document.getElementById("receipts-list");
  list.replaceChildren();
  if (!items.length) {
    list.append(emptyMessage("暂无同步回执。"));
    return;
  }
  items.forEach((item) => list.append(listItem(item.profile_version, `${item.manifest.claims.length} claims`, item.status)));
}

document.getElementById("account-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const message = document.getElementById("account-message");
  const values = Object.fromEntries(new FormData(form));
  try {
    await api("/api/accounts", { method: "POST", body: JSON.stringify(values) });
    form.reset();
    message.className = "form-message";
    message.textContent = "账号引用已添加。";
    await Promise.all([loadAccounts(), loadDashboard()]);
  } catch (error) {
    message.className = "form-message error";
    message.textContent = error.message;
  }
});

document.getElementById("space-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const message = document.getElementById("space-message");
  const values = Object.fromEntries(new FormData(form));
  try {
    await api("/api/spaces", { method: "POST", body: JSON.stringify(values) });
    form.reset();
    message.className = "form-message";
    message.textContent = "身份空间已创建。";
    await Promise.all([loadSpaces(), loadDashboard()]);
  } catch (error) {
    message.className = "form-message error";
    message.textContent = error.message;
  }
});

document.getElementById("claim-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const message = document.getElementById("claim-message");
  const values = Object.fromEntries(new FormData(form));
  try {
    await api("/api/claims", { method: "POST", body: JSON.stringify(values) });
    form.reset();
    message.className = "form-message";
    message.textContent = "候选资料已添加，等待确认。";
    await Promise.all([loadClaims(), loadDashboard(), loadEvents()]);
  } catch (error) {
    message.className = "form-message error";
    message.textContent = error.message;
  }
});

document.getElementById("confirm-all").addEventListener("click", async () => {
  await api("/api/claims/confirm-all", { method: "POST", body: "{}" });
  await Promise.all([loadClaims(), loadDashboard(), loadEvents()]);
});

document.getElementById("import-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const message = document.getElementById("import-message");
  try {
    const { item } = await api("/api/imports", { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(form))) });
    message.className = "form-message";
    message.textContent = `已导入 ${item.messages} 条消息，新增 ${item.candidates} 条候选。`;
    await Promise.all([loadClaims(), loadDashboard(), loadEvents()]);
  } catch (error) {
    message.className = "form-message error";
    message.textContent = error.message;
  }
});

document.getElementById("route-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const message = document.getElementById("route-message");
  try {
    await api("/api/routes", { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(form))) });
    message.className = "form-message";
    message.textContent = "同步路线已创建，发送前请先预览。";
    await Promise.all([loadRoutes(), loadDashboard(), loadEvents()]);
  } catch (error) {
    message.className = "form-message error";
    message.textContent = error.message;
  }
});

document.getElementById("scan-device").addEventListener("click", async () => {
  const button = document.getElementById("scan-device");
  button.disabled = true;
  try {
    await api("/api/devices/scan", { method: "POST", body: "{}" });
    await Promise.all([loadDevices(), loadDashboard(), loadEvents()]);
  } catch (error) {
    window.alert(error.message);
  } finally {
    button.disabled = false;
  }
});

document.getElementById("privacy-toggle").addEventListener("click", async () => {
  const action = sensitiveSyncEnabled ? "disable" : "enable";
  if (!sensitiveSyncEnabled && !window.confirm("开启后数据仍会受每条路线策略控制。发送到第三方后，ContextVault 无法保证对方删除或忘记内容。确定开启吗？")) return;
  await api(`/api/privacy/${action}`, { method: "POST", body: "{}" });
  await Promise.all([loadPrivacy(), loadEvents()]);
});

Promise.all([loadDashboard(), loadAccounts(), loadSpaces(), loadClaims(), loadEvents(), loadDevices(), loadRoutes(), loadPrivacy(), loadReceipts()]).catch((error) => {
  document.querySelector("main").dataset.error = error.message;
});
