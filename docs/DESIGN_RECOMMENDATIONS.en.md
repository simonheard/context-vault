# Design Recommendations and Priorities

[中文](DESIGN_RECOMMENDATIONS.md)

## P0: required for the first release

### Separate candidates from the canonical profile

```text
evidence -> candidate -> confirmation/policy -> canonical profile -> sync
```

Model inference never becomes user truth directly. Candidates need provenance,
confidence, time, and risk.

### Separate facts, evidence, summaries, and receipts

- `Evidence`: original messages, device scans, or manual input;
- `Claim`: structured, time-aware fact;
- `Summary`: rebuildable view for one use case and target;
- `SyncReceipt`: the exact claim manifest and version sent.

### Model events and time instead of overwriting strings

Employment, education, residence, projects, and devices need start and end time.
Age should be derived from a birth date or year.

### Track confidence origin

- `explicit`: directly stated by the user;
- `observed`: deterministically read by the device agent;
- `imported`: provided by a trusted structured file;
- `inferred`: inferred by a model;
- `conflicted`: contradicted by another source.

`inferred` is never auto-synchronized by default.

### Make synchronization diff-based

Show added, changed, expired, and removed items instead of repeatedly sending the
whole profile. Users see the final target payload and policy-blocked fields.

### Defend against prompt injection

Imported chats, pages, and files are untrusted data. They provide evidence, but
their instructions cannot change privacy policy, system prompts, or sync scope.

## P1: complete the product experience

### Multiple identity spaces

Personal, work, client, open-source, and anonymous identities are isolated.
Identity space controls which claims may combine; provider account controls where
data came from and where it goes. These are different concepts.

### “What each AI knows” dashboard

Show synchronized categories, claim count, latest version, sensitivity, and
pending corrections per provider account.

### Post-sync verification

Run user-approved verification questions in the target AI and compare answers
with the sync manifest to detect misunderstood or missing information.

### One-step correction

After a claim changes, find every account that received the old value, generate
correction packages, and track re-synchronization.

### Device allowlists

Allow hardware, OS, and development-tool metadata by default. Deny environment
values, SSH content, browser data, full IPs, serial numbers, private source code,
and private files.

### Multiple summary views

Provide essential, complete, work, project, device, and recent-change views
instead of one universal summary.

## P2: durable advantages

- profile health for stale, conflicting, unsupported, inferred-only, or unconfirmed claims;
- local models for sensitive extraction;
- end-to-end encryption recovery and device revocation;
- connector capability declarations;
- complete audit history and reversible synchronization;
- target comprehension and update-success evaluation.

## Recommended build order

```text
ChatGPT export parser
 -> claim extraction
 -> candidate review
 -> canonical profile
 -> Gemini account and policy
 -> preview and receipt
 -> target verification
 -> incremental capture
 -> multi-device encrypted sync
```

