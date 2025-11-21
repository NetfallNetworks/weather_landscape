# Web Worker (Isolated Environment)

This directory contains the web worker with its own isolated Python environment.

## Why Isolated?

The web worker is a pure HTTP server (704 lines) that only needs to:
- Serve HTML pages (landing, forecasts, guide, admin)
- Serve static assets (CSS, favicon, diagram, example image)
- Read weather images from R2 bucket
- Manage KV storage (active ZIPs, format configurations)
- Enqueue jobs to the fetch queue

It does NOT need:
- Pillow (image processing/generation)
- Sprite assets for rendering
- Drawing/rendering code (p_weather modules)
- Weather data fetching utilities
- Image generation utilities
- R2 upload utilities

By isolating it in its own directory with a minimal `pyproject.toml`, we ensure the deployment bundle contains ONLY what's needed.

## Structure

```
workers/web/
├── pyproject.toml         # NO dependencies!
├── wrangler.toml          # Worker configuration (template)
├── wrangler.local.toml    # Generated with actual IDs (git-ignored)
└── src/
    ├── web.py             # Main worker (704 lines)
    ├── web_utils.py       # Minimal utilities (templates, KV, R2 reading)
    └── assets/
        ├── templates/     # HTML files
        │   ├── admin.html
        │   ├── forecasts.html
        │   ├── guide.html
        │   └── landing.html
        ├── favicon.png
        ├── diagram.png
        ├── example.bmp
        └── styles.css
```

**Note:** Code is in `src/` subdirectory to prevent venv bundling. When `uv run` creates `.venv-workers/` in the parent directory, it won't get bundled into the worker.

## Deployment

Deploy from project root using:
```bash
./deploy-all.sh
```

Or deploy just the web worker:
```bash
cd workers/web
uv run pywrangler deploy -c wrangler.local.toml
```

## Dependencies

**Production:** None! Zero dependencies.
**Dev:** `workers-py>=1.7.0` (Cloudflare Workers runtime)

The web worker has NO production dependencies, resulting in:
- Faster cold starts (no Pillow loading)
- Smaller bundle size (~200KB vs ~13MB)
- **98.5% bundle size reduction!**
- Reduced memory footprint
- Faster deployments
- Only necessary assets bundled

## What Was Removed?

Compared to the original root-level deployment, the optimized web worker eliminates:
- ❌ Pillow library (~10MB)
- ❌ All sprite images used for rendering
- ❌ p_weather drawing/rendering modules (~378KB)
- ❌ WeatherLandscape rendering class
- ❌ Image generation utilities
- ❌ R2 upload code
- ❌ Weather fetching utilities (geocoding, OWM API calls)
- ❌ Unnecessary config classes

## What Was Kept?

Only the essentials:
- ✅ HTML template loading and rendering
- ✅ CSS and static asset serving
- ✅ KV utilities (get/add/remove active ZIPs, format configs)
- ✅ R2 reading (list objects, get images)
- ✅ Queue producer (enqueue fetch jobs)
- ✅ Format configuration constants
- ✅ Admin dashboard functionality

## Routes Served

**Public Routes:**
- `GET /` - Landing page with links to all ZIPs
- `GET /forecasts` - Forecasts page showing all available ZIPs
- `GET /guide` - Guide page with documentation
- `GET /{zip}` - Latest weather image for ZIP (default format)
- `GET /{zip}?{format}` - Weather image in specific format
- `GET /example` - Example weather image

**Admin Routes (Protected):**
- `GET /admin` - Admin dashboard
- `GET /admin/status` - Status endpoint with metadata
- `GET /admin/formats?zip={zip}` - Get formats for ZIP
- `POST /admin/activate?zip={zip}` - Activate ZIP for regeneration
- `POST /admin/deactivate?zip={zip}` - Deactivate ZIP
- `POST /admin/formats/add?zip={zip}&format={format}` - Add format
- `POST /admin/formats/remove?zip={zip}&format={format}` - Remove format
- `POST /admin/generate?zip={zip}` - Manually trigger generation

## Performance Comparison

| Metric | Before (Root) | After (Isolated) | Improvement |
|--------|--------------|------------------|-------------|
| Bundle Size | ~13MB | ~200KB | **98.5% smaller** |
| Dependencies | Pillow + shared | 0 | **100% reduction** |
| Cold Start | Slow (Pillow load) | Fast | **Significantly faster** |
| Memory | High | Low | **Much lower** |

## Benefits

1. **Blazing Fast Cold Starts:** No Pillow or heavy dependencies to load
2. **Minimal Bundle:** Only HTML, CSS, and minimal utilities
3. **Lower Costs:** Reduced memory and CPU usage
4. **Faster Deployments:** Smaller bundle uploads faster
5. **Cleaner Architecture:** Clear separation of concerns
6. **Better Maintainability:** Easy to see exactly what the web worker does

This is the final worker to be optimized, completing the isolation of all workers in the Weather Landscape system!
