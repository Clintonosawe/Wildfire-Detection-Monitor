# Architecture

## Boundaries
- `core.py`: pure parsing, numerical validation, distance, scoring, and allowed transitions.
- `store.py`: SQLite schema, transactions, deterministic batch ordering, incident read model, audit events, GeoJSON.
- `server.py`: local HTTP adapter with exact route allowlist, loopback binding, host/origin validation, response CSP, bounded review payloads.
- `static/`: vanilla JavaScript using textContent for supplied values; no CDN dependencies.
- `__main__.py`: import and run commands. CSV batches are capped at 5 MB / 5,000 rows.

## Persistence
One incident has many detections and many events. Detection IDs hash six-decimal coordinates, acquisition time, and satellite. Same-key corrections are skipped, not applied. Incident IDs are based on the first inserted detection. Imports validate fully before writes; a failed write rolls back the batch. Review state and event creation share a transaction. Data survives restarts.

Grouping compares incoming points with fixed incident anchors, using great-circle distance ≤10 km and absolute time difference ≤24 hours. Choose the nearest anchor, then ID as tie-breaker. Rows are sorted within each batch. Different import batch order can produce different groupings. No transitive clustering, automatic merging, spread estimation, or cross-sensor pixel reconciliation is implied. Closed incidents can receive new matching observations without reopening; operator review is manual. Anchors remain fixed even if later points are more intense.

## HTTP contract
| Method | Path | Behavior |
|---|---|---|
| GET | `/api/health` | Version and basic app health |
| GET | `/api/incidents` | Incidents with observations, score components and events |
| GET | `/api/export` | GeoJSON points at incident anchors |
| POST | `/api/review` | `{id, action, note}`; returns `{ok:true}` |

Review actions: `reviewing`, `confirmed`, `dismissed`, `resolved`, `report`. New → reviewing → confirmed → resolved; reviewing → dismissed; dismissed/resolved → reviewing. `report` adds an unverified event without changing status. Notes must contain 3–1000 trimmed characters. Invalid input returns 400, unknown route 404, disallowed origin/host 403.

## Capacity and deployment
Single-process HTTPServer and SQLite prioritize inspectability over concurrency. Ingestion scans existing anchors (worst-case quadratic), and reads embed full evidence history. The row cap is a guard, not a performance guarantee. Large datasets need spatial indexing, pagination, migrations and query benchmarks. There is no automatic database upgrade mechanism; schema is v0.1 only. A public service would require authenticated roles, HTTPS, request timeouts, rate limits, durable audit identity, backup/restore, and a production server.
