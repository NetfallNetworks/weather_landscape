# Weather Fetcher Worker (Isolated Environment)

This directory contains the weather fetcher worker with its own isolated Python environment.

## Why Isolated?

The fetcher is lightweight (103 lines) and only needs to:
- Geocode ZIP codes via OpenWeatherMap API
- Fetch current weather and forecast data
- Store weather data in KV

It does NOT need:
- Pillow (image processing)
- Sprite assets or images
- Drawing/rendering code (p_weather modules)
- HTML templates or CSS
- R2 upload utilities

By isolating it in its own directory with a minimal `pyproject.toml`, we ensure the deployment bundle contains ONLY what's needed.

## Structure

```
workers/fetcher/
├── pyproject.toml         # NO Pillow dependency!
├── wrangler.toml          # Worker configuration (template)
├── wrangler.local.toml    # Generated with actual KV IDs (git-ignored)
├── weather_fetcher.py     # Main worker (103 lines)
├── kv_utils.py            # Minimal KV utilities (geocoding, OWM fetch, storage)
└── config.py              # Minimal config (WorkerConfig, to_js, format constants)
```

## Deployment

Deploy from project root using:
```bash
./deploy-all.sh
```

Or deploy just the fetcher:
```bash
cd workers/fetcher
./deploy.sh  # Recommended - auto-cleans venv before/after deploy
```

**Manual deployment (without venv cleanup):**
```bash
cd workers/fetcher
uv run pywrangler deploy -c wrangler.local.toml
```

**Purge virtual environments:**
If you encounter venv bundling issues, manually purge:
```bash
cd workers/fetcher
./purge-venv.sh
```

## Dependencies

**Production:** None! Zero dependencies.
**Dev:** `workers-py>=1.7.0` (Cloudflare Workers runtime)

The fetcher has NO production dependencies, resulting in:
- Faster cold starts
- Smaller bundle size (~15KB vs entire shared library + Pillow)
- Reduced memory footprint
- Faster deployments
- No unnecessary asset bundling

## What Was Removed?

Compared to the original bundled deployment, the optimized fetcher eliminates:
- ❌ Pillow library (~10MB)
- ❌ All sprite images (.bmp, .png files)
- ❌ p_weather drawing/rendering modules
- ❌ HTML templates
- ❌ CSS files
- ❌ Image utilities
- ❌ R2 upload code
- ❌ WeatherLandscape class

## What Was Kept?

Only the essentials:
- ✅ Geocoding logic with KV caching
- ✅ OpenWeatherMap API calls
- ✅ Weather data storage in KV
- ✅ Queue message handling
- ✅ Minimal configuration
