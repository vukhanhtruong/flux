# Web UI

React 19 + TypeScript + Vite 7 + Tailwind CSS v4 frontend.

## Tech Stack

- **React 19** with TypeScript
- **Vite 7** for build tooling
- **React Router DOM v7** for routing
- **Tailwind CSS v4** for styling

## Structure

```
packages/web-ui/src/
├── components/    # Reusable UI components
├── pages/         # Route-level components
├── api/           # API client and types
├── hooks/         # Custom React hooks
└── utils/         # Helper functions
```

## API Consumption

- REST API at `http://localhost:8000` (FastAPI backend)
- Nginx proxies `/api/*` to backend in production

## Development

```bash
npm install
npm run dev       # Dev server on port 5173
npm run build     # Production build
npm run preview   # Preview production build
```

## Production

Single Docker container serves both:
- Nginx serves static files from `/app/web-ui/dist/`
- Nginx proxies `/api/*` to FastAPI on port 8000
