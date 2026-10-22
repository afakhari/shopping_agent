# Typed contracts

These are **target version-1 contracts**, not a claim that legacy endpoints already conform.

- mission-event: sequenced events on a durable mission with allowlisted event types.
- contact-result: provenance-aware merchant inquiry, including simulated channel.
- visit-plan: handoff card fields for navigation and seller backup.

Use the JSON Schema draft-2020-12 validator in backend contract tests after application code is imported. Generate or maintain matching TypeScript definitions and assert UI/backend parity. Changing a breaking field requires a new version and migration policy.
