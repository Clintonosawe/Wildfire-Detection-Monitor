# ADR 001 — Use a transparent priority baseline
Status: accepted for prototype; revisit after labeled evaluation.

Context: the original K-means experiment had no verified labels, and synthetic community responses cannot establish wildfire accuracy.

Decision: expose a deterministic weighted triage score and component breakdown. Do not call it a probability or an AI detector. Store unverified reports without changing scores.

Consequences: easy to test and inspect; scientific weights and thresholds remain unvalidated. Weather missingness can lower scores. A learned model requires the evaluation protocol and a versioned data pipeline first.
