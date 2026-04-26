---
paths:
  - "packages/web-ui/**/*.ts"
  - "packages/web-ui/**/*.tsx"
  - "packages/web-ui/**/*.css"
---

# React Frontend Patterns

## Tech Stack

- React 19 with TypeScript
- Vite 7 for build tooling
- React Router DOM v7 for routing
- Tailwind CSS v4 for styling

## Component Structure

```
packages/web-ui/src/
├── components/    # Reusable UI components
├── pages/         # Route-level components
├── api/           # API client and types
├── hooks/         # Custom React hooks
└── utils/         # Helper functions
```

## API Consumption

- REST API at port 8000 (FastAPI backend)
- Use fetch or axios for API calls
- Type API responses with TypeScript interfaces

## Development

```bash
npm run dev       # Dev server on port 5173
npm run build     # Production build
npm run preview   # Preview production build
```

## Testing

- Component tests with React Testing Library
- Type checking with TypeScript
