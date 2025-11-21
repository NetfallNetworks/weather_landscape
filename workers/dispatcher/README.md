# Job Dispatcher Worker (Isolated Environment)

This directory contains the job dispatcher worker with its own isolated Python environment.

## Why Isolated?

The dispatcher is lightweight (78 lines) and only needs to:
- Read format configurations from KV
- Fan out weather-ready events into individual generation jobs
- Enqueue jobs to the landscape-jobs queue

It does NOT need:
- Pillow (image processing)
- Sprite assets or images
- Drawing/rendering code (p_weather modules)
- HTML templates or CSS
- R2 upload utilities
- Weather fetching code

By isolating it in its own directory with a minimal `pyproject.toml`, we ensure the deployment bundle contains ONLY what's needed.

## Structure

```
workers/dispatcher/
├── pyproject.toml         # NO dependencies!
├── wrangler.toml          # Worker configuration (template)
├── wrangler.local.toml    # Generated with actual KV IDs (git-ignored)
└── src/
    ├── dispatcher.py      # Main worker (78 lines)
    └── dispatcher_utils.py # Minimal utilities (get_formats_for_zip, to_js, configs)
```

**Note:** Code is in `src/` subdirectory to prevent venv bundling. When `uv run` creates `.venv-workers/` in the parent directory, it won't get bundled into the worker.

## Deployment

Deploy from project root using:
```bash
./deploy-all.sh
```

Or deploy just the dispatcher:
```bash
cd workers/dispatcher
uv run pywrangler deploy -c wrangler.local.toml
```

## Dependencies

**Production:** None! Zero dependencies.
**Dev:** `workers-py>=1.7.0` (Cloudflare Workers runtime)

The dispatcher has NO production dependencies, resulting in:
- Faster cold starts
- Smaller bundle size (~15KB vs entire shared library + Pillow)
- Reduced memory footprint
- Faster deployments
- No unnecessary asset bundling

## What Was Removed?

Compared to the original bundled deployment, the optimized dispatcher eliminates:
- ❌ Pillow library (~10MB)
- ❌ All sprite images (.bmp, .png files)
- ❌ p_weather drawing/rendering modules
- ❌ HTML templates
- ❌ CSS files
- ❌ Image utilities
- ❌ R2 upload code
- ❌ WeatherLandscape class
- ❌ Geocoding and weather fetching code
- ❌ Asset loading utilities

## What Was Kept?

Only the essentials:
- ✅ get_formats_for_zip() - Read format configs from KV
- ✅ to_js() - Convert Python objects to JavaScript
- ✅ FORMAT_CONFIGS and DEFAULT_FORMAT constants
- ✅ Queue message handling
- ✅ Job fan-out logic
