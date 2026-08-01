# Product Plan

[中文](PRODUCT_PLAN.md)

## Product definition

ContextVault is a personal memory synchronization layer across AI assistants.
It does not merely answer “where are my chats?” It answers:

> What does each AI know about me, what is still true, what may be shared, and
> how can those profiles stay synchronized automatically?

The system extracts structured information from conversations, official
exports, local devices, and user input; maintains a canonical personal profile;
and synchronizes policy-filtered versions to Gemini, Claude, ChatGPT, and future
tools.

## Typical scenarios

### ChatGPT to Gemini

A user has talked with ChatGPT for two years. ContextVault imports that history
and discovers age, school, major, work, location, languages, response
preferences, projects, and goals. After one consolidated review, it creates a
Gemini-ready profile. Later changes are synchronized incrementally.

### Devices and development environments

A user owns a MacBook, Windows desktop, VPS, and phone. A local agent records
models, OS versions, important software, development tools, project locations,
and approved non-sensitive configuration. When the user asks an AI for help,
the assistant already knows the correct environment.

### Information changes

An old conversation says the user works at Company A; a new one says they have
joined Company B. The system ends the validity of A, marks B as the candidate
current employer, and asks for confirmation when necessary.

## Personal information coverage

The first stage supports:

- identity: name, age, birthday, languages, timezone, and location;
- education: school, major, degree, periods, courses, and certificates;
- employment: company, role, team, responsibilities, work style, and periods;
- preferences: response, communication, writing, code, food, travel, and shopping;
- skills and goals: abilities, learning, long-term goals, and plans;
- projects and decisions: stack, status, important decisions, and tasks;
- relationships: important people and relationships explicitly confirmed by the user;
- devices and environments: hardware, OS, software, development environments, network roles, and non-sensitive settings;
- life events: moves, job changes, graduation, and device purchases.

Medical, financial, legal, precise-address, and government-identifier data may
be modeled, but is not automatically shared across platforms. Passwords, OTPs,
private keys, API keys, cookies, and session tokens never enter the profile.

## Core loop

```text
collect -> extract candidates -> normalize -> resolve time/conflicts -> policy/review
  -> canonical profile -> target summary -> sync -> receipt and change history
```

### Collection

- official exports from ChatGPT, Claude, and Gemini;
- user-approved incremental capture from a browser extension;
- device information from a CLI/local agent;
- manual forms, Markdown, JSON, and clipboard input;
- later: optional calendar, contact, repository, and smart-home connectors.

### Extraction and normalization

Natural language becomes a sourced `Claim`, for example:

```text
entity: user
attribute: employment.current.company
value: Example Corp
source: ChatGPT conversation abc / message 123
confidence: 0.96
status: candidate
sensitivity: private
validity: 2025-03 to present
```

Age should not be stored permanently as a static number. Prefer birth date or
birth year and derive age at use time. Employment, education, location, and
device state also require validity periods.

### Review and policy

Not every item requires individual confirmation:

- low-risk, explicitly stated claims may be auto-confirmed;
- ordinary personal data can be reviewed in batches;
- inferred, conflicting, or sensitive claims require confirmation;
- credentials and secrets are rejected.

### Automatic summaries

The same canonical profile can produce:

- a 100–200 word essential bio;
- a complete personal profile;
- current work and skills;
- a project context pack;
- a device and development environment inventory;
- a change digest since the previous sync;
- provider-specific packages for Gemini, Claude, and ChatGPT.

### Synchronization

Each target has its own allowed categories, sensitivity ceiling, size limit,
frequency, and preview policy. The browser extension writes only in a page where
the user is already signed in and has allowed the action. Cookies are never
uploaded and the server never impersonates the user.

Sensitive information uses three modes: `block` (never send), `ask` (confirm
every time), and `allow` (automatic sync within an explicit scope). Policies are
per provider and category rather than one global switch. `secret` data can never
be configured as `allow`.

## MVP

### MVP 1 — ChatGPT profile extractor

- Parse ChatGPT official exports.
- Extract identity, education, employment, location, preferences, skills, projects, and devices.
- Display provenance, confidence, conflicts, and validity.
- Let users confirm in batches.
- Export canonical JSON and readable Markdown.

Acceptance: produce a useful, traceable profile from years of chat history in
under 15 minutes.

### MVP 2 — Gemini sync

- Generate a Gemini-optimized summary.
- Provide sync preview and field filters.
- Synchronize through user-triggered copy, file import, or browser injection.
- Record sync versions and changes.

Acceptance: Gemini correctly uses approved profile facts and preferences while
receiving none of the prohibited fields.

### MVP 3 — Device agent

- Scan model, CPU, memory, OS, package managers, key software, and development tools.
- Configure which paths and settings may be synchronized.
- Deduplicate devices and track last-seen time and changes.
- Generate inventory and troubleshooting environment summaries.

Acceptance: an AI distinguishes the user's devices and gives advice for the
correct environment.

### MVP 4 — Incremental automatic sync

- Capture explicitly allowed new messages through the extension.
- Extract incrementally and detect changes.
- Auto-sync low-risk fields according to policy.
- Route conflicts and sensitive changes to review.
- Add end-to-end encrypted multi-device synchronization.

## Later capabilities

- **Relationship and family graph:** only user-confirmed important relationships.
- **Timeline:** education, employment, residence, device, and project changes.
- **Reversible sync:** track what was sent where and generate correction/deletion instructions.
- **Multiple identity modes:** personal, work, client, and anonymous profiles.
- **Context views:** send only the subset relevant to the current task.
- **Right to be forgotten:** local deletion, correction requests, tombstones, and backup cleanup.
- **Profile health:** flag stale, conflicting, unsupported, or unconfirmed claims.
- **Deterministic extraction:** prefer rules for devices and explicit structured fields.
- **Optional local model:** extract sensitive data without a cloud model.
- **Consent receipts:** retain the notice version, categories, target, choice, and revocation time.

## Success metrics

- More than 95% accuracy among confirmed extracted claims.
- More than 90% of claims link to an original message or device scan.
- Less than 15 minutes from import to the first Gemini package.
- Fewer than 20% of incremental candidates require manual work.
- No credential-class secret is stored.
- Users can clearly answer “which platform knows which information about me?”

## Product principles

1. The canonical profile is the source of truth; chats are evidence.
2. Automation depends on risk rather than being universally on or off.
3. New information must be able to expire old information.
4. Every cross-platform write is previewable, traceable, and reversible.
5. Device configuration and user information belong to one profile but use different collection and sensitivity policies.
6. Processing is local by default; the server provides only end-to-end encrypted sync.
7. Disclaimers support informed consent; they never replace safety controls or shift all responsibility to the user.
