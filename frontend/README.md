# Autom8r Frontend

React 18 + TypeScript + Vite chat UI for the Autom8r backend (FastAPI).
Plain modern CSS, `useState`/`useEffect` state, native `fetch` — no
component library, no state library.

The UI talks to the backend defined in `../docs/api-contract.md`: it sends
chat turns, renders the assistant reply, shows the currently captured lead,
and lists tool activity per turn.

## Run

```bash
npm install
npm run dev
```

Dev server: http://localhost:5173 — expects the backend at
http://localhost:8000 (`uvicorn app.main:app` from `../backend`).

## Configuration

The backend base URL is read from `VITE_API_BASE_URL` and falls back to
`http://localhost:8000`:

```bash
# .env.local
VITE_API_BASE_URL=http://localhost:8000
```

## Scripts

- `npm run dev` — start the Vite dev server (port 5173)
- `npm run build` — type-check (`tsc -b`) and build production assets to `dist/`
- `npm run preview` — serve the production build locally

## Structure

- `src/types/` — TypeScript types mirroring the frozen API contract
- `src/services/api.ts` — typed fetch wrappers; all failures throw `ApiError`
- `src/components/` — ChatWindow, ChatMessage, LeadPanel, ToolActivity,
  StatusBadge, EmptyState
- `src/styles.css` — design tokens (slate/indigo palette, 8px spacing
  scale) and all component styles
