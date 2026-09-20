# Frontend — Sovereign AI Workbench

The client/user-experience layer: User Workbench, Admin Dashboard, agent
selection, chat, file upload, execution-progress, and deliverable UI. This
package is **UI only** — no model access, no business logic. Everything it
needs from the outside world goes through [`src/services/api`](src/services/api).

## Stack

React 19 · Vite · TypeScript · Tailwind CSS v4 · lucide-react ·
react-router-dom — intentionally minimal, no heavy UI/animation/state
libraries.

## Running

```bash
npm install
npm run dev
```

- User Workbench: `http://localhost:5173/`
- Admin Dashboard: `http://localhost:5173/admin`

The dev server binds to all interfaces (`server.host: true` in
`vite.config.ts`), so it's also reachable at `http://SERVER-IP:5173` from
another machine on the LAN.

## Configuration

Copy `.env.example` to `.env` to override defaults:

```
VITE_API_BASE_URL=http://localhost:8000   # backend origin (see ../backend)
VITE_MAX_UPLOAD_MB=25
```

`config.apiBaseUrl` (`src/lib/config.ts`) falls back to
`http://localhost:8000` when the env var is unset, so local dev works out
of the box; set `VITE_API_BASE_URL=http://SERVER-IP:8000` for a LAN
deployment.

## Backend integration (Segments 2 & 3)

`src/services/api/client.ts` calls the real FastAPI backend (`../backend`)
for everything except conversation history and Network/System/Audit Logs
(no persistence or telemetry endpoints exist yet — see `backend/README.md`
→ "Intentionally not implemented yet"):

- `getAgents()` — `GET /api/agents` (icons are still resolved locally by id)
- `sendMessage()` — `POST /api/chat`, including real citations and
  deliverables from Document/Data Agent RAG and tool use, mapped into the
  existing `ChatMessage`/`ExecutionStep`/`Citation`/`Deliverable` shapes.
  Selecting the **Auto** option (alongside the five agents, in the
  welcome cards and the header switcher — see `AgentSelection` in
  `src/types/agent.ts`) omits `agent_id`; the backend's Task Router picks
  a concrete agent per turn and its one-sentence reason rides along on the
  existing `"selecting_agent"` execution step's `detail` — no new UI
  component needed for that to be visible.
- `uploadFile()` — `POST /api/files/upload` (real bytes, saved server-side;
  the returned `path` rides along on the attachment so agents/tools can
  read the actual file — see `AttachmentRef` in `backend/app/agents/base.py`)
- `downloadDeliverable()` — `GET /api/deliverables/{id}`, then triggers an
  actual browser save (`DeliverableCard`'s download button)
- `getModels()` / `addModel()` / `deleteModel()` — `GET/POST /api/admin/models`,
  `POST /api/models`, `DELETE /api/models/{id}`
- `getAdminOverview()` — `GET /api/admin/overview`

Every backend call goes through a small `request()` helper that turns a
failed fetch or a non-2xx response into a clean `Error` with a readable
message, which the UI already surfaces gracefully (the chat `ErrorMessage`
component, or an inline error line on the Admin Overview/Models pages)
instead of crashing or silently showing stale data.

## Structure

```
src/
├── components/   # layout, chat, agents, files, execution, deliverables, admin, common
├── pages/        # UserWorkbench, AdminDashboard
├── routes/       # AppRoutes (/ and /admin)
├── context/      # WorkbenchContext (agent, conversation, message state)
├── services/
│   ├── api/      # stable API surface consumed by components
│   └── mock/     # mock data + delay helpers backing that API today
├── hooks/
├── types/
├── lib/          # utils, env config
├── App.tsx
└── main.tsx
```

## Scripts

| Command | Purpose |
|---|---|
| `npm run dev` | Start the Vite dev server |
| `npm run build` | Type-check (`tsc -b`) and produce a production build |
| `npm run preview` | Preview the production build locally |
| `npm run lint` | Run oxlint |
