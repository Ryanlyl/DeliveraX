# React Admin Dashboard

React admin template with React 18, TypeScript, Vite 5, Ant Design v5, React Router v6, and Zustand v4.

## Tech Stack

- React 18.3.1
- TypeScript 5.2.2
- Vite 5.3.1
- Ant Design 5.18.3
- React Router 6.23.1
- Zustand 4.5.2
- Ant Design Charts 2.2.3

## Project Structure

```
src/
├── components/layout/    # Layout components (Sidebar, Header, Content, Breadcrumb)
├── router/              # Router configuration with auto-import
├── store/               # Zustand state management
└── views/               # Page components and route definitions
```

## Key Features

### Auto Route Importing

Routes are automatically loaded from `views/**/*.router.tsx` files using Vite's `import.meta.glob`.

Route definition example:
```typescript
const routes: AdminRouterItem[] = [{
  path: 'demo',
  element: <DemoPage />,
  meta: { label: "Demo", title: "Demo", key: "/demo", icon: <Icon /> },
  children: [...]
}]
export default routes
```

### Layout Components

Built-in layout system with:
- Sidebar (auto-generated from routes)
- Header
- Content area
- Breadcrumb (auto-generated from routes)
- Footer

### Theme Switching

Theme management via Zustand store (`src/store/config.ts`):
- Light/Dark/Compact modes
- Primary color customization
- Algorithm-based theme switching

### State Management

Zustand stores in `src/store/`:
- `config.ts` - Theme configuration

## Development

- Node.js 18+ or 20+ required
- Routes: Create `*.router.tsx` files in `views/` directories
- Layout: Components in `src/components/layout/`
- State: Add Zustand stores in `src/store/`

