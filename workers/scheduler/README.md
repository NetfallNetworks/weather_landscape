# ZIP Scheduler Worker (Isolated Environment)

This directory contains the ZIP scheduler worker with its own isolated Python environment.

## Why Isolated?

The scheduler is extremely lightweight (65 lines) and only needs to:
- Read ZIP codes from KV
- Enqueue messages to a queue

It does NOT need:
- Pillow (image processing)
- Sprite assets
- Weather processing libraries
- HTML templates or CSS

By isolating it in its own directory with a minimal `pyproject.toml`, we ensure the deployment bundle contains ONLY what's needed.

## Structure

```
workers/scheduler/
├── pyproject.toml       # NO Pillow dependency!
├── wrangler.toml        # Worker configuration (template)
├── wrangler.local.toml  # Generated with actual KV IDs (git-ignored)
└── src/
    ├── zip_scheduler.py    # Main worker (65 lines)
    └── scheduler_utils.py  # Minimal utilities (40 lines)
```

## Deployment

Deploy from project root using:
```bash
./deploy-all.sh
```

Or deploy just the scheduler:
```bash
cd workers/scheduler
uv run pywrangler deploy -c wrangler.local.toml
```

## Dependencies

**Production:** None! Zero dependencies.
**Dev:** `workers-py>=1.7.0` (Cloudflare Workers runtime)

The scheduler has NO production dependencies, resulting in:
- Faster cold starts
- Smaller bundle size
- Reduced memory footprint
- Faster deployments
