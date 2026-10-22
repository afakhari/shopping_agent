# Bazaar Compass Web

React + TypeScript + Vite, RTL-first. At this scaffold stage, the UI shell and backend liveness status work; catalog search is intentionally marked as not wired yet.

## Commands

```bash
npm install
npm run dev
npm run lint
npm run typecheck
npm test
npm run build
```

Node.js 22.12+ is required by Vite 8. Direct dependencies are pinned exactly. The current build environment could not reach the npm registry, so `package-lock.json` is not generated yet. Run `npm install` in a network-enabled environment and commit the generated lockfile; then switch Dockerfile installation to `npm ci`.

`VITE_API_BASE_URL` must never contain secrets. In development, `/api` is proxied to `VITE_DEV_API_TARGET` or `http://127.0.0.1:8000`.
