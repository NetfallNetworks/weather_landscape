# CLAUDE.md

## Testing Policy

Tests must pass before shipping. No exceptions.

The workflow is:
1. Run tests — validate all existing tests pass
2. Write new tests for your change
3. Implement the change
4. Run tests — validate all tests pass (old and new)

If tests don't pass at step 1, stop and fix them before doing anything else. Do not start work on a broken suite.

Tests must never be "gamed" — no weakening assertions, no skipping failures, no removing tests to make the suite green. Broken tests mean broken code; fix the code, not the test. No tests are better than gamed tests.

## Running Tests Locally

```bash
# Run local image generation test
python run_test.py

# Run local generation with API calls
python test_local_generation.py

# Run local dev server
python run_server.py
```

### Worker-Specific Testing

Each worker can be tested independently with wrangler:

```bash
# Test individual workers locally
cd workers/scheduler && npx wrangler dev
cd workers/fetcher && npx wrangler dev
cd workers/dispatcher && npx wrangler dev
cd workers/landscape && npx wrangler dev
cd workers/web && npx wrangler dev
```

### Deploy All Workers

```bash
# One-command deployment (regenerates configs and deploys all 5 workers)
./deploy-all.sh
```

## Project Structure

This repo contains a weather visualization system deployed as 5 isolated Cloudflare Workers connected via Queues:

1. **zip-scheduler** (`workers/scheduler/`) — Cron-triggered (15min), enqueues active ZIPs for processing
2. **weather-fetcher** (`workers/fetcher/`) — Queue consumer, fetches weather from OpenWeatherMap, stores in KV
3. **job-dispatcher** (`workers/dispatcher/`) — Queue consumer, creates one job per format (fan-out pattern)
4. **landscape-generator** (`workers/landscape/`) — Queue consumer, generates images with Pillow, uploads to R2
5. **weather-landscape-web** (`workers/web/`) — HTTP handler, serves UI and image endpoints

Supporting files:
- `run_test.py` / `test_local_generation.py` — Local testing scripts
- `run_server.py` — Local dev server
- `deploy-all.sh` — One-command deployment for all workers
- `setup-local-config.sh` — Generate local wrangler configs from templates
- `esp32/` — E-Ink display module (MicroPython)
- `templates/` — Sprite assets and image templates
- `pic/` — Documentation images

## QA Review Process

After each phase's code is complete and tests pass, run the **4-agent QA review** before marking the phase done. The process is documented in `plan/README.md` under "QA Review Process". The four lenses are: Code Quality, Security Hardening, Test Quality, and Maintainability — all run as parallel Sonnet agents.

## Configuration Management

This project uses a template-based configuration approach:
- `wrangler.toml` files contain `YOUR_KV_NAMESPACE_ID` placeholders
- `.wrangler.local.env` contains actual KV namespace IDs (git-ignored)
- `setup-local-config.sh` generates local configs by substituting values
- Never commit actual KV namespace IDs or secrets to version control
