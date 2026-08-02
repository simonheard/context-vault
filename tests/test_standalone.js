const assert = require("node:assert/strict");
const {
  contextVaultEmptyStandalone,
  contextVaultNormalizeStandalone,
  contextVaultContainsSecret,
  contextVaultStandaloneCandidates,
  contextVaultStandaloneProfile,
  contextVaultStandaloneDue,
} = require("../extension/standalone.js");

const candidates = contextVaultStandaloneCandidates([
  { role: "user", content: "My name is Sam. I prefer dark mode." },
]);
assert.equal(candidates.length, 2);
assert.equal(candidates[0].attribute, "identity.name");
assert.equal(contextVaultStandaloneCandidates([{ role: "assistant", content: "My name is Sam" }]).length, 0);
assert.equal(contextVaultStandaloneCandidates([{ role: "assistant", content: "My name is Sam" }], true)[0].confidence, 0.5850000000000001);
assert.equal(contextVaultContainsSecret("token=abcdefghijklmnopqrstuvwxyz123456"), true);

const vault = contextVaultEmptyStandalone();
vault.claims.push({ id: "1", attribute: "preference.editor", value: "VS Code", sensitivity: "personal", status: "confirmed" });
vault.claims.push({ id: "2", attribute: "identity.name", value: "Sam", sensitivity: "private", status: "pending" });
vault.claims.push({ id: "3", attribute: "health.note", value: "Sensitive note", sensitivity: "sensitive", status: "confirmed" });
assert.match(contextVaultStandaloneProfile(vault).content, /VS Code/);
assert.doesNotMatch(contextVaultStandaloneProfile(vault).content, /Sam/);
assert.doesNotMatch(contextVaultStandaloneProfile(vault).content, /Sensitive note/);
assert.match(contextVaultStandaloneProfile(vault, true).content, /Sensitive note/);
assert.equal(contextVaultStandaloneDue({ enabled: true, riskAcknowledgedAt: "now", intervalMinutes: 5 }), true);
assert.equal(contextVaultStandaloneDue({ enabled: true, riskAcknowledgedAt: "now", pausedReason: "failed" }), false);

const imported = contextVaultNormalizeStandalone({ claims: [
  { id: "ok", attribute: "preference.editor", value: "Vim", status: "confirmed" },
  { id: "bad", attribute: "auth.token", value: "token=abcdefghijklmnopqrstuvwxyz123456", status: "confirmed" },
] });
assert.equal(imported.claims.length, 1);
console.log("standalone extension tests passed");
