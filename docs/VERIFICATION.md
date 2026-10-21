# Verification record

Local verification: 2026-10-20, Python 3.12.14.

- 21 automated tests passed: domain rules, persistence and real localhost HTTP integration.
- JavaScript syntax check passed with Node.js.
- Fresh demo import produced 10 observations; six grouped incidents.
- GitHub CI is configured for Python 3.11–3.13 but has not run remotely.
- Browser-based interaction and visual checks were attempted but could not run because this environment lacks a Chromium executable. Browser layout, accessibility, and interaction need a manual pass before public release.
- No live NASA/weather/SMS integration or scientific accuracy testing was performed.

Reproduce: `python -m unittest discover -s tests -v` and `node --check emberwatch/static/app.js`.

Manual acceptance checklist:
1. Run demo and serve; verify six incidents and ten observations.
2. Select a high-priority incident and compare its component total with its score.
3. Enter a note and move new → reviewing → confirmed → resolved.
4. Refresh and verify state and timeline persist.
5. Add an unverified report; confirm score/status do not change.
6. Filter by status; inspect an empty queue and mobile layout.
7. Export GeoJSON and verify longitude precedes latitude.
