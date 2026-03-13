# flux Web UI

Modern web dashboard for the flux personal finance agent, built with React 19, TypeScript, Vite 7, and Tailwind CSS v4.

## Development

```bash
cd packages/web-ui
npm install
npm run dev       # Dev server on http://localhost:5173
npm run build     # Production build
npm run preview   # Preview production build
npm test          # Run tests
```

## Configuration

Create a `.env` file (see `.env.example`):

```env
VITE_API_BASE_URL=http://localhost:8000
```

In production, the web UI is served as static files by Nginx, which proxies `/api/` requests to the FastAPI backend.

## Tech Stack

- **React 19** with TypeScript
- **Vite 7** for build tooling
- **Tailwind CSS v4** for styling
- **React Router DOM v7** for routing
- **Vitest** for testing
