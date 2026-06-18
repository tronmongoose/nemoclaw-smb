# NemoClaw SMB Ops — Dashboard UI

Dark command-center dashboard for the NemoClaw SMB Ops Agent.

## Run

```bash
cd ui
npm install
npm run dev
```

Open http://localhost:5173

## API base URL

Set `VITE_API_BASE` in a `.env` file (defaults to `http://localhost:8000`):

```
VITE_API_BASE=http://localhost:8000
```

## Build

```bash
npm run build   # TypeScript check + Vite bundle -> dist/
```

## Panel / endpoint map

| Panel | Endpoint(s) |
|---|---|
| Header — audit badge | `GET /audit?limit=100` (polled 5s) |
| Knowledge Graph | `GET /graph` |
| Invoice Feed | `GET /invoices?limit=50`, `GET /invoices/anomalies?threshold=2.0` |
| Approval Queue | `GET /approvals/pending` (polled 5s), `POST /approvals/{id}/decide` |
| Savings | `GET /savings/summary`, `GET /savings/alternatives?current_vendor=...` |

All panels fail gracefully to an empty/skeleton state when the API is offline.
