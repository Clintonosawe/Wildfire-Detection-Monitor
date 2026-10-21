# ADR 002 — Local-first, standard-library application
Status: accepted for v0.1.

Context: reviewers should reproduce the project without paid API accounts or package installation.

Decision: Python standard library, SQLite, and vanilla browser JavaScript; offline synthetic fixture; CLI imports. Bind HTTP to loopback and enforce same-origin mutations.

Consequences: low setup friction and transactional persistence. No multi-user security, production server, map tiles, automatic live ingestion, or horizontal scaling. Use a proper web framework/production stack when M5 requirements justify it.
