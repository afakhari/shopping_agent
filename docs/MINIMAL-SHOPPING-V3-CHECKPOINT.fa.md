# Minimal Shopping v3 QA checkpoint

Snapshot of the user's requested correction after the negative screenshot review. The application changes already exist in main at `588af2533a8eca1a0acf51a2e1ce5a38df77a3cf`. This pull request adds a validation record only so that one CI run tests the consolidated UI changes.

- Removed the fixed 4-stage dashboard/navigation entirely.
- Removed redundant title/subtitle/explanation and trust copy from the purchase surface.
- Moved assistant explanation and demo-data disclaimers to accessible native details.
- Tightened product cards to image/title/price/shop/badges/2 actionable buttons.
- Kept offer details, OSM maps and price freshness in expandable sections; no API or DB changes.
- Active design imported from `frontend/src/minimal-v3.css`; historical CSS no longer imported.
- Updated RTL/accessibility/visual-contract tests.
- Browser acceptance still pending at 1440px, 390px and 320px, with interactions.

Do not treat CI success as pixel-perfect visual validation. Do not run CI separately for intermediate commits.
