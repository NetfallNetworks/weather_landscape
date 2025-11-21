# Landscape Generator Worker (Isolated Environment)

This directory contains the landscape generator worker with its own isolated Python environment.

## Why Isolated?

The landscape generator is focused on image generation and needs:
- Pillow (image processing) - **unavoidable 10MB**
- p_weather rendering modules
- Templates and sprite assets
- KV reading (weather data)
- R2 uploading (generated images)

It does NOT need:
- OpenWeatherMap API code (weather is pre-fetched)
- Geocoding utilities (coordinates come in job data)
- HTML templates or CSS (web-only)
- Scheduler logic
- Job dispatcher code
- Weather fetcher code

By isolating it in its own directory with minimal dependencies, we reduce the deployment bundle by ~15.5% (~1.9MB).

## Structure

```
workers/landscape/
├── pyproject.toml              # Only Pillow dependency
├── wrangler.toml               # Worker configuration (template)
├── wrangler.local.toml         # Generated with actual KV IDs (git-ignored)
├── README.md                   # This file
└── src/                        # Source code (prevents venv bundling)
    ├── landscape_generator.py  # Main worker (149 lines)
    ├── landscape_utils.py      # Minimal utilities (KV, R2, configs)
    ├── configs.py              # Format configuration classes
    ├── weather_landscape.py    # WeatherLandscape rendering class
    ├── asset_loader.py         # Asset loading utilities
    └── p_weather/              # Weather rendering modules
        ├── template_rgb.bmp    # RGB template (149KB)
        ├── template_wb.bmp     # B&W template (5KB)
        ├── sprite/             # B&W sprites (~50KB, 122 PNGs)
        ├── sprite_rgb/         # RGB sprites (~50KB, 100+ PNGs)
        ├── configuration.py    # Base configuration
        ├── openweathermap.py   # Weather data parsing
        ├── sunrise.py          # Sunrise/sunset calculations
        ├── holidays.py         # Holiday/birthday logic
        └── sprites_*.py        # Sprite definitions
```

**Note:** Code is in `src/` subdirectory to prevent venv bundling. When `uv run` creates `.venv-workers/` in the parent directory, it won't get bundled into the worker.

## Deployment

Deploy from project root using:
```bash
./deploy-all.sh
```

Or deploy just the landscape generator:
```bash
cd workers/landscape
uv run pywrangler deploy -c wrangler.local.toml
```

## Dependencies

**Production:**
- Pillow >= 10.0.0 (image processing - **required**)

**Dev:**
- workers-py >= 1.7.0 (Cloudflare Workers runtime)

The landscape generator has minimal dependencies compared to the original shared deployment:
- Faster deployments (no unnecessary code)
- Smaller bundle size (~10.3MB vs ~12.2MB)
- Cleaner dependency graph
- Self-contained and easier to maintain

## What Was Removed?

Compared to the original bundled deployment in `src/workers/`, the optimized landscape generator eliminates:
- ❌ OpenWeatherMap API fetching code (uses pre-fetched data from KV)
- ❌ Geocoding utilities (coordinates provided in job data)
- ❌ HTML templates and CSS (web worker only)
- ❌ Scheduler logic and cron utilities
- ❌ Job dispatcher code
- ❌ Fetcher worker code
- ❌ Unnecessary shared module bloat (~2MB)

## What Was Kept?

Only the essentials for image generation:
- ✅ Pillow library (10MB - unavoidable, needed for image processing)
- ✅ p_weather rendering modules (weather landscape drawing)
- ✅ Templates (RGB and B&W .bmp files)
- ✅ Sprite assets (RGB and B&W .png files)
- ✅ get_weather_data() - Read weather from KV
- ✅ upload_to_r2() - Upload generated images
- ✅ WorkerConfig - Minimal configuration system
- ✅ FORMAT_CONFIGS - Format definitions
- ✅ WeatherLandscape - Image generation class
- ✅ Asset loading utilities

## Bundle Size Comparison

```
Before (shared deployment):  ~12.2MB
  - Pillow:           10MB
  - shared/ code:     2MB (bloated with unused utilities)
  - templates:        154KB
  - sprites:          100KB

After (isolated):            ~10.3MB
  - Pillow:           10MB (unavoidable)
  - landscape code:   50KB (optimized)
  - templates:        154KB (necessary)
  - sprites:          100KB (necessary)

Savings: ~1.9MB (15.5% reduction)
```

## How It Works

1. **Queue Consumer**: Listens to `landscape-jobs` queue for generation jobs
2. **Read Weather Data**: Fetches pre-cached weather data from KV (no API calls)
3. **Generate Image**: Uses WeatherLandscape class to render the image in the specified format
4. **Upload to R2**: Stores the generated image in the WEATHER_IMAGES R2 bucket
5. **Save Metadata**: Stores generation metadata in KV for tracking

The generator processes jobs in batches (max 10 jobs per batch) with automatic retries on failure.
