# Project charter and delivery plan

## Objective
Turn the joint wildfire hackathon concept into a reproducible portfolio application that demonstrates data engineering, geospatial reasoning, explainable prioritization, and disciplined software delivery.

Primary user: a researcher reviewing candidate thermal observations. Success for v0.1: a fresh checkout runs without credentials; malformed data never partially imports; repeated ingestion is idempotent; decisions persist with notes; automated tests pass. This is not a claim of emergency readiness.

## Roles
Clinton: proposed integration/documentation owner. Classmate: proposed data/science reviewer, subject to agreement. Assign real issue ownership together; no completed collaboration or review is implied by this plan.

## Milestones
| Milestone | Scope | State |
|---|---|---|
| M1 / reproducible core | validation, grouping, scoring, SQLite | Implemented |
| M2 / analyst workflow | dashboard, transitions, audit, export | Implemented |
| M3 / repository readiness | tests, CI definition, templates, documentation | Implemented locally; remote CI pending |
| M4 / evaluated data integration | live adapters, weather provenance, labeled benchmark | Planned |
| M5 / multi-user pilot | authentication, deployment, observability, consent | Planned; gated on validation |

## Prioritized backlog
| ID | Priority | Deliverable | Acceptance criteria |
|---|---|---|---|
| EW-01 | P0 | Retire exposed legacy secrets | Provider keys rotated; source/history scanned before publishing |
| EW-02 | P0 | Co-author attribution and license | Both contributors agree on attribution and licensing |
| EW-03 | P1 | FIRMS API adapter | Env-only key, HTTPS, timeout, retries with backoff, quotas, cached fixture tests, no secrets in logs |
| EW-04 | P1 | Weather provenance | Weather source/time stored, units normalized, freshness window enforced, absent data explicit |
| EW-05 | P1 | Evaluation dataset | Label provenance, geographic/temporal splits, uncertainty and false-alert analysis documented |
| EW-06 | P1 | Public deployment foundation | Auth roles, CSRF/session design, HTTPS, rate limits, production server, migrations, backups tested |
| EW-07 | P2 | Spatial scale | Benchmark 10k/100k records; indexed grouping; documented resource budgets |
| EW-08 | P2 | Consented notifications | Opt-in registry, unsubscribe, delivery outbox, retries, idempotency; sandbox-provider tests |
| EW-09 | P2 | Observation corrections | Versioned source updates; stable identity across sensors and imports |
| EW-10 | P2 | Basemap and accessibility QA | Offline-safe map option, keyboard review, screen-reader and contrast checks |

Use GitHub Project columns **Backlog → Ready → In progress → In review → Done**. Fields: priority, owner, milestone, estimate, acceptance criteria. Limit in-progress work to one issue per person. Break issues larger than two focused work sessions into smaller deliverables. Hold a short weekly review and record actual decisions; do not invent historical sprints.

## Definition of Ready
Problem, acceptance criteria, dependencies, and proposed owner are clear. Data or credential requirements have a feasible plan.

## Definition of Done
Acceptance criteria verified; relevant regression tests pass; README/API changes documented; no secrets or personal data; limitation notes updated; collaborator review completed where possible. Link issue → branch → pull request → release. For public releases, check CI on GitHub and record actual results.

## Risk register
| Risk | Impact | Mitigation / owner role |
|---|---|---|
| Anomaly mistaken for wildfire | Misleading claims | Explicit triage language; evaluation gate / science reviewer |
| Legacy keys exposed | Account abuse | Rotate at providers; history cleanup / maintainer |
| Synthetic demo confused with live data | Misrepresentation | Source badges, timestamps, separate DBs / UI owner |
| Missing weather lowers scores | Biased prioritization | Missingness indicator, evaluation slices / data owner |
| Grouping depends on import order | Inconsistent incident identity | Document; design reconciliation / backend owner |
| Public exposure without identity | Unauthorized edits | Loopback only; deployment gate / maintainer |
| Human reports contain personal details | Privacy leakage | No phone fields; local-only notes; avoid PII / reviewer |

## Release checklist
Run tests; execute fresh-database demo; review attribution; rotate original secrets; confirm no databases/caches in git; attach a real dashboard screenshot; verify CI after push; tag `v0.1.0` only after collaborator review. Track real bugs as issues rather than silently treating this plan as completed history.
