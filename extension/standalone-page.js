const claimsRoot = document.getElementById("claims");
const status = document.getElementById("message");

function say(value) {
  status.textContent = value;
  window.setTimeout(() => { if (status.textContent === value) status.textContent = ""; }, 3000);
}

async function render() {
  const vault = await contextVaultStandaloneLoad();
  const pending = vault.claims.filter((item) => item.status === "pending").length;
  const confirmed = vault.claims.filter((item) => item.status === "confirmed").length;
  document.getElementById("stats").textContent = `${confirmed} 已确认 · ${pending} 待审阅`;
  claimsRoot.replaceChildren();
  for (const claim of [...vault.claims].reverse()) {
    const row = document.createElement("article");
    row.className = `claim ${claim.status}`;
    const body = document.createElement("div");
    const attribute = document.createElement("strong");
    attribute.textContent = claim.attribute;
    const value = document.createElement("p");
    value.textContent = claim.value;
    const meta = document.createElement("p");
    meta.className = "meta";
    meta.textContent = `${claim.status} · ${claim.sensitivity} · ${claim.provider || "manual"}`;
    body.append(attribute, value, meta);
    const actions = document.createElement("div");
    actions.className = "claim-actions";
    for (const [label, next] of [["确认", "confirmed"], ["拒绝", "rejected"]]) {
      const button = document.createElement("button");
      button.textContent = label;
      button.className = next === "rejected" ? "secondary" : "";
      button.disabled = claim.status === next;
      button.addEventListener("click", async () => {
        const current = await contextVaultStandaloneLoad();
        const target = current.claims.find((item) => item.id === claim.id);
        if (target) target.status = next;
        await contextVaultStandaloneSave(current);
        await render();
      });
      actions.append(button);
    }
    row.append(body, actions);
    claimsRoot.append(row);
  }
}

document.getElementById("confirm-all").addEventListener("click", async () => {
  const vault = await contextVaultStandaloneLoad();
  vault.claims.forEach((item) => { if (item.status === "pending") item.status = "confirmed"; });
  await contextVaultStandaloneSave(vault); await render(); say("候选已确认");
});

document.getElementById("clear-rejected").addEventListener("click", async () => {
  const vault = await contextVaultStandaloneLoad();
  vault.claims = vault.claims.filter((item) => item.status !== "rejected");
  await contextVaultStandaloneSave(vault); await render(); say("已清理拒绝项");
});

document.getElementById("export").addEventListener("click", async () => {
  const vault = await contextVaultStandaloneLoad();
  const blob = new Blob([JSON.stringify(vault, null, 2)], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob); link.download = `contextvault-browser-${new Date().toISOString().slice(0, 10)}.json`; link.click();
  URL.revokeObjectURL(link.href); say("备份已导出");
});

document.getElementById("import").addEventListener("change", async (event) => {
  const file = event.target.files?.[0]; if (!file) return;
  const parsed = contextVaultNormalizeStandalone(JSON.parse(await file.text()));
  for (const collection of [parsed.captures, parsed.routes]) {
    for (const item of Object.values(collection)) {
      item.enabled = false; item.riskAcknowledgedAt = null; item.pendingReceipt = null;
    }
  }
  await contextVaultStandaloneSave(parsed); await render(); say("备份已导入");
});

document.getElementById("add-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const values = Object.fromEntries(new FormData(event.currentTarget));
  if (contextVaultContainsSecret(values.value)) { say("检测到凭证或秘密，已拒绝保存"); return; }
  const vault = await contextVaultStandaloneLoad();
  if (vault.claims.length >= 5000) { say("独立资料库已达到 5000 条上限，请导出并迁移到 CLI"); return; }
  vault.claims.push({ id: crypto.randomUUID(), attribute: values.attribute.trim(), value: values.value.trim(), sensitivity: values.sensitivity, confidence: 1, status: "confirmed", provider: "manual", createdAt: new Date().toISOString() });
  await contextVaultStandaloneSave(vault); event.currentTarget.reset(); await render(); say("资料已添加");
});

render();
