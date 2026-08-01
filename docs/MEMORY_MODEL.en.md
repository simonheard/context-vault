# Profile and Memory Model

[中文](MEMORY_MODEL.md)

## Why claims

“The user is 28” is not a permanent text memory. Prefer “birth year is 1998,”
retain its source, and derive age when needed. Employment, residence, and device
ownership also require time ranges, provenance, and current status.

The smallest unit is therefore a Claim: an evidence-backed statement about one
entity, one attribute, and one value.

## Attribute taxonomy

```text
identity.*          name, birthday, languages, timezone
location.*          country, city, frequent places
education.*         school, major, degree, courses, certificates
employment.*        company, role, team, responsibilities, work style
preference.*        responses, writing, code, food, travel, shopping
skill.*             skill, proficiency, learning status
goal.*              short- and long-term goals
project.*           project, stack, status, decisions, tasks
relationship.*      user-confirmed important people and relationships
device.*            model, hardware, OS, software, configuration
event.*             moves, jobs, graduation, device purchases
health.*            sensitive; automatic sync disabled by default
finance.*           sensitive; automatic sync disabled by default
legal.*             sensitive; automatic sync disabled by default
attachment.*        provider reference, description, status, optional extracted text
```

An attachment is not a binary Claim value. A Claim may reference an
`AttachmentRef`; the database stores text and references while the source AI
provider continues to host the original file.

## Sensitivity levels

- `public`: information the user is willing to publish;
- `personal`: ordinary profile data governed by target policy;
- `private`: preview required by default;
- `sensitive`: explicit confirmation for every cross-platform sync;
- `secret`: rejected and never stored.

Sensitivity describes the data; sync mode describes the user's authorization
for one target. They are not the same concept.

- `block`: never send;
- `ask`: confirm each item before every sync;
- `allow`: permit automatic sync for the specified target and categories;
- `secret` is always forced to `block` and cannot be overridden.

## Automation rules

- An explicit, non-conflicting “I now work at X” may enter batch review.
- An AI inference such as “you probably live in X” stays `candidate` and cannot auto-sync.
- A deterministic OS version from the device agent may be auto-confirmed under an allowlist.
- A new claim that conflicts with a current claim creates a conflict rather than overwriting it.
- An explicit change expression supersedes the old claim and ends its validity.
- Independent sources may raise confidence while preserving every provenance record.

## Example target policy

```json
{
  "target": "gemini",
  "allowed_categories": [
    "identity.language",
    "education.current",
    "employment.current",
    "preference.response",
    "skill",
    "project.active",
    "device.summary"
  ],
  "max_sensitivity": "personal",
  "sensitive_mode": "ask",
  "require_preview_on_first_sync": true,
  "auto_sync_low_risk_changes": true,
  "summary_budget_chars": 12000
}
```

Enabling sensitive sync affects future operations only. Revocation stops future
sync but cannot guarantee that an AI provider has forgotten previously received
data. The system should show send history and correction/deletion guidance.

## Device configuration boundary

Allowed: model, OS, CPU, memory, disk capacity, approved applications, language
versions, package managers, container tools, editors, project aliases, and
non-sensitive settings.

Denied by default: passwords, private keys, API keys, cookies, browser tokens,
environment variable values, Wi-Fi passwords, complete serial numbers, recovery
keys, and private file contents.
