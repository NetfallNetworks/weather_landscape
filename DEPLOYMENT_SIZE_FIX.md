# Deployment Size Issue

## Problem
Dev dependencies (aiohttp, workers-py) are being bundled despite being in `[dependency-groups]`.
Deployment shows ~5MB of vendored modules when it should only be ~500KB (pillow only).

## Root Cause
Pywrangler correctly reads only production dependencies from `[project.dependencies]`, but `uv pip install` may be resolving against `uv.lock` which includes dev dependencies.

## Attempted Solutions

### 1. Clean build cache (TRY THIS FIRST)
```bash
rm -rf .venv-workers python_modules .wrangler
uv run pywrangler deploy
```

### 2. If that doesn't work
This may be a pywrangler limitation. Consider filing an issue at:
https://github.com/cloudflare/workers-py/issues

The fix would be for pywrangler to use `uv export --no-dev` or pass appropriate flags to exclude dev dependencies during sync.

## Files Changed
- `.gitignore` - Ignore build artifacts (`.venv-workers/`, `python_modules/`)
- `.wranglerignore` - Exclude test files and docs from bundle
