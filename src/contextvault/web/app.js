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
  const { counts } = await api("/api/dashboard");
  document.getElementById("metric-claims").textContent = counts.claims;
  document.getElementById("metric-candidates").textContent = counts.candidates;
  document.getElementById("metric-accounts").textContent = counts.accounts;
  document.getElementById("metric-devices").textContent = counts.devices;
  document.getElementById("review-notice").hidden = counts.candidates === 0;
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

Promise.all([loadDashboard(), loadAccounts(), loadSpaces(), loadClaims(), loadEvents()]).catch((error) => {
  document.querySelector("main").dataset.error = error.message;
});
