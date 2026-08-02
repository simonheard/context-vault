# Bidirectional web capture

[中文](CAPTURE.md)

The extension both pushes profile updates and pulls information from web conversations where the user is already signed in and has explicitly enabled capture.

## Pull modes

1. **Current-conversation capture:** reads the current page immediately or on schedule. Normal capture extracts candidates only from user messages, so provider hallucinations do not become user facts.
2. **Knowledge-probe conversation:** on a blank new chat, the extension asks what that AI remembers, waits for a stable answer, and captures it. Provider answers use a `0.65` confidence multiplier and always remain reviewable candidates.

```bash
contextvault captures enable <account-id> --interval 15 \
  --conversation-url https://chatgpt.com/ --acknowledge-privacy-risk
contextvault captures list
```

For push routes without a binding, the extension creates a new chat and binds its stable URL after the first send. Receipts move through `prepared -> dispatching -> sent_unconfirmed -> completed`. A possible click is never retried automatically; recovery searches for the receipt marker and otherwise asks the user to resolve the ambiguous state.

Three consecutive adapter failures trip a circuit breaker. Experimental providers fail closed when selectors are unavailable. Capture never reads cookies, passwords, the complete conversation list, or tabs outside configured provider hosts.
