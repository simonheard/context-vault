const CONTEXTVAULT_STANDALONE_KEY = "standaloneVault";
const CONTEXTVAULT_STANDALONE_SCHEMA = 1;

function contextVaultEmptyStandalone() {
  return {
    schema: CONTEXTVAULT_STANDALONE_SCHEMA,
    claims: [],
    captures: {},
    routes: {},
    receipts: [],
    updatedAt: new Date().toISOString(),
  };
}

function contextVaultNormalizeStandalone(value) {
  const empty = contextVaultEmptyStandalone();
  if (!value || typeof value !== "object") return empty;
  const claims = Array.isArray(value.claims) ? value.claims.filter((item) => {
    return item && typeof item === "object"
      && typeof item.attribute === "string" && item.attribute.length > 0 && item.attribute.length <= 160
      && typeof item.value === "string" && item.value.length > 0 && item.value.length <= 10000
      && ["pending", "confirmed", "rejected"].includes(item.status)
      && !contextVaultContainsSecret(item.value);
  }).slice(-5000) : [];
  return {
    ...empty,
    ...value,
    schema: CONTEXTVAULT_STANDALONE_SCHEMA,
    claims,
    captures: value.captures && typeof value.captures === "object" ? value.captures : {},
    routes: value.routes && typeof value.routes === "object" ? value.routes : {},
    receipts: Array.isArray(value.receipts) ? value.receipts.slice(-200) : [],
  };
}

async function contextVaultStandaloneLoad() {
  const saved = await chrome.storage.local.get([CONTEXTVAULT_STANDALONE_KEY]);
  return contextVaultNormalizeStandalone(saved[CONTEXTVAULT_STANDALONE_KEY]);
}

async function contextVaultStandaloneSave(vault) {
  const normalized = contextVaultNormalizeStandalone(vault);
  normalized.updatedAt = new Date().toISOString();
  await chrome.storage.local.set({ [CONTEXTVAULT_STANDALONE_KEY]: normalized });
  return normalized;
}

function contextVaultContainsSecret(value) {
  return [
    /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/,
    /\b(?:sk-|gh[pousr]_|glpat-|npm_|xox[baprs]-)[A-Za-z0-9_-]{20,}\b/,
    /\b(?:password|passwd|pwd|api[_-]?key|secret|token)\s*[:=]\s*\S{8,}/i,
    /\bBearer\s+[A-Za-z0-9._~+/=-]{20,}/i,
  ].some((pattern) => pattern.test(value));
}

const CONTEXTVAULT_STANDALONE_PATTERNS = [
  ["identity.name", /(?:my name is|我是|我叫)\s*([^\n。.!！]{1,80})/i, "private"],
  ["location.current", /(?:i live in|我住在|我目前在)\s*([^\n。.!！]{1,120})/i, "private"],
  ["employment.organization", /(?:i work at|我在)\s*([^\n。.!！]{1,120}?)(?:工作|上班|$)/i, "private"],
  ["education.organization", /(?:i study at|我在)\s*([^\n。.!！]{1,120}?)(?:读书|上学|学习|$)/i, "private"],
  ["language.spoken", /(?:i speak|我会说|我使用)\s*([^\n。.!！]{1,100})/i, "personal"],
  ["preference.general", /(?:i prefer|我喜欢|我偏好)\s*([^\n。.!！]{1,160})/i, "personal"],
  ["device.owned", /(?:i use|我的(?:电脑|手机|设备)(?:是|有)?)\s*([^\n。.!！]{1,160})/i, "personal"],
];

function contextVaultStandaloneCandidates(messages, knowledgeProbe = false) {
  const role = knowledgeProbe ? "assistant" : "user";
  const scale = knowledgeProbe ? 0.65 : 1;
  const found = [];
  for (const message of messages || []) {
    if (message.role !== role || contextVaultContainsSecret(String(message.content || ""))) continue;
    const content = String(message.content || "");
    for (const [attribute, pattern, sensitivity] of CONTEXTVAULT_STANDALONE_PATTERNS) {
      const match = content.match(pattern);
      const value = match?.[1]?.trim();
      if (!value || contextVaultContainsSecret(value)) continue;
      found.push({ attribute, value, sensitivity, confidence: 0.9 * scale });
    }
  }
  return found;
}

async function contextVaultStandaloneIngest(capture, knowledgeProbe = false) {
  const vault = await contextVaultStandaloneLoad();
  const candidates = contextVaultStandaloneCandidates(capture.messages, knowledgeProbe);
  let added = 0;
  for (const candidate of candidates) {
    if (vault.claims.length >= 5000) break;
    const duplicate = vault.claims.some((item) => item.attribute === candidate.attribute && item.value === candidate.value && item.status !== "rejected");
    if (duplicate) continue;
    vault.claims.push({
      id: crypto.randomUUID(),
      ...candidate,
      status: "pending",
      provider: capture.provider,
      conversationUrl: capture.conversation_url,
      sourceTitle: capture.title,
      createdAt: new Date().toISOString(),
    });
    added += 1;
  }
  await contextVaultStandaloneSave(vault);
  return { messages: capture.messages.length, candidates: added, pending: vault.claims.filter((item) => item.status === "pending").length };
}

function contextVaultStandaloneProfile(vault, includeSensitive = false) {
  const claims = vault.claims.filter((item) => item.status === "confirmed" && item.sensitivity !== "secret" && (includeSensitive || item.sensitivity !== "sensitive"));
  const lines = ["# ContextVault profile", "", ...claims.map((item) => `- ${item.attribute}: ${item.value}`)];
  return { content: `${lines.join("\n").trim()}\n`, claims };
}

async function contextVaultStandaloneDigest(value) {
  const bytes = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), (item) => item.toString(16).padStart(2, "0")).join("");
}

async function contextVaultStandaloneConfigure(kind, provider, options) {
  const vault = await contextVaultStandaloneLoad();
  const collection = kind === "capture" ? vault.captures : vault.routes;
  collection[provider] = {
    ...(collection[provider] || {}),
    provider,
    enabled: Boolean(options.enabled),
    intervalMinutes: Math.max(5, Math.min(10080, Number(options.intervalMinutes || 60))),
    riskAcknowledgedAt: options.enabled ? new Date().toISOString() : null,
    conversationUrl: options.conversationUrl || collection[provider]?.conversationUrl || null,
    consecutiveFailures: 0,
    pausedReason: null,
    updatedAt: new Date().toISOString(),
  };
  await contextVaultStandaloneSave(vault);
  return collection[provider];
}

function contextVaultStandaloneDue(item, now = Date.now()) {
  if (!item?.enabled || !item.riskAcknowledgedAt || item.pausedReason) return false;
  const last = Date.parse(item.lastRunAt || "");
  return !Number.isFinite(last) || now - last >= Number(item.intervalMinutes || 60) * 60000;
}

async function contextVaultStandaloneFailure(kind, provider, reason) {
  const vault = await contextVaultStandaloneLoad();
  const collection = kind === "capture" ? vault.captures : vault.routes;
  const item = collection[provider];
  if (!item) return null;
  item.consecutiveFailures = Number(item.consecutiveFailures || 0) + 1;
  item.lastError = String(reason || "adapter_failed").slice(0, 300);
  if (item.consecutiveFailures >= 3) item.pausedReason = "three_consecutive_adapter_failures";
  await contextVaultStandaloneSave(vault);
  return item;
}

if (typeof module !== "undefined") {
  module.exports = {
    contextVaultEmptyStandalone,
    contextVaultNormalizeStandalone,
    contextVaultContainsSecret,
    contextVaultStandaloneCandidates,
    contextVaultStandaloneProfile,
    contextVaultStandaloneDue,
  };
}
