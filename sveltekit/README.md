# SvelteKit Entity Management UI

A SvelteKit conversion of the Angular Entity Management UI. This provides a metadata-driven CRUD interface for managing entities via REST API.

## Features

- **Dynamic Entity Management**: Metadata-driven forms and lists
- **Multiple View Modes**: List, Details, Edit, Create
- **Foreign Key Relationships**: ObjectId field handling with selectors
- **Real-time Validation**: Client and server-side validation
- **Responsive Design**: Bootstrap-based responsive UI
- **Type Safety**: Full TypeScript support

## Equivalent Angular Routes

This SvelteKit app provides the exact same functionality as your Angular UI:

- `/` → Dashboard (entities-dashboard.component)
- `/entity/[entityType]` → Entity List (entity-list.component) 
- `/entity/[entityType]/create` → Create Form (entity-form.component)
- `/entity/[entityType]/[id]` → Details View (entity-form.component)
- `/entity/[entityType]/[id]/edit` → Edit Form (entity-form.component)

## Configuration

The API URL can be configured in `src/lib/config.ts` or via environment variable:

```bash
# Set API URL (defaults to http://localhost:3000/api)
export VITE_API_URL=http://localhost:3000/api
```

## Developing

Start the development server:

```bash
npm run dev
# or
npm run dev -- --open
```

This will start the SvelteKit dev server on a different port than your Angular app, so you can run both simultaneously for comparison.

## Building

Create a production build:

```bash
npm run build
```

Preview the production build:

```bash
npm run preview
```

## TypeScript

Type checking:

```bash
npm run check
# or with watch mode
npm run check:watch
```

## Architecture Comparison

### Angular → SvelteKit Conversion

| Angular Concept | SvelteKit Equivalent |
|----------------|---------------------|
| Services | Svelte Stores |
| Components | Svelte Components |
| Dependency Injection | Import/Export |
| RxJS Observables | Svelte Stores |
| Angular Router | SvelteKit File-based Routing |
| Angular Forms | Native Form Handling |
| HttpClient | Fetch API |

### Key Improvements

- **Simpler State Management**: Svelte stores vs Angular services
- **Less Boilerplate**: No decorators, less ceremony
- **Better Performance**: Compile-time optimizations
- **Smaller Bundle**: No framework runtime overhead
- **Easier Debugging**: Clearer component lifecycle
