# Debugging Distributed Tracing

Quick guide to debug trace ID propagation through your queue pipeline.

## Step 1: Add Debug Code to web.py

In `_handle_generate` method (around line 669), add debugging:

```python
from shared import (
    to_js,
    generate_trace_id,
    add_trace_context,
    debug_trace_propagation  # Add this
)

async def _handle_generate(self, env, query_params):
    """Handle POST /admin/generate"""
    try:
        zip_code = query_params.get('zip')
        if not zip_code or not (zip_code.isdigit() and len(zip_code) == 5):
            return Response.new(
                json.dumps({'error': 'Invalid ZIP code. Must be 5 digits.'}),
                {'status': 400, 'headers': {'Content-Type': 'application/json'}}
            )

        # Generate trace ID
        trace_id = generate_trace_id()
        print(f"🔍 Generated trace_id: {trace_id}")

        # Enqueue to fetch-jobs
        job = {
            'zip_code': zip_code,
            'scheduled_at': datetime.utcnow().isoformat() + 'Z'
        }

        # Add trace context
        job = add_trace_context(job, trace_id=trace_id)

        # DEBUG: Show what we're sending
        debug_trace_propagation(job, worker_name="web")

        await env.FETCH_JOBS.send(to_js(job))

        return Response.new(
            json.dumps({
                'success': True,
                'zip': zip_code,
                'trace_id': trace_id,
                'message': f'Generation queued for ZIP {zip_code}'
            }),
            headers=to_js({'Content-Type': 'application/json'})
        )
    except Exception as e:
        # ... error handling
```

## Step 2: Add Debug Code to weather_fetcher.py

In the `queue` method (around line 59), add debugging:

```python
from shared import (
    WorkerConfig,
    geocode_zip,
    store_weather_data,
    fetch_weather_from_owm,
    to_js,
    debug_message,  # Add this
    extract_trace_context,  # Add this
    get_trace_id  # Add this
)

async def queue(self, batch, env, ctx):
    """Queue consumer handler - processes fetch jobs"""
    env = self.env

    print(f"Weather Fetcher received {len(batch.messages)} job(s)")

    # Get configuration
    config = WorkerConfig(env)
    if not config.OWM_KEY:
        print("ERROR: OWM_API_KEY not set")
        for message in batch.messages:
            message.retry()
        return

    success_count = 0
    error_count = 0

    for message in batch.messages:
        try:
            # DEBUG: Show the raw message
            debug_message(message, worker_name="weather_fetcher")

            # Parse job data
            job = json.loads(JSON.stringify(message.body))
            zip_code = job['zip_code']

            # Extract trace context
            trace_context = extract_trace_context(message)
            trace_id = get_trace_id(trace_context)

            print(f"🔍 Extracted trace_id: {trace_id}")

            # ... rest of the code ...
```

## Step 3: Deploy and Test

1. **Deploy the web worker:**
   ```bash
   uv run pywrangler deploy -c wrangler.local.toml
   ```

2. **Deploy the weather fetcher:**
   ```bash
   uv run pywrangler deploy -c wrangler.fetcher.local.toml
   ```

3. **Trigger a generation** from the admin UI or via curl:
   ```bash
   curl -X POST "https://your-worker.workers.dev/admin/generate?zip=78729"
   ```

4. **Check the logs** in Cloudflare dashboard:
   - Go to Workers & Pages → Select worker → Logs
   - Look for the debug output

## What to Look For

### In web worker logs:
```
🔍 Generated trace_id: abc123def456...
=== DEBUG OUTGOING MESSAGE from web ===
{
  "zip_code": "78729",
  "scheduled_at": "2025-01-15T10:30:00Z",
  "_trace": {
    "trace_id": "abc123def456...",
    "span_id": "xyz789",
    "parent_span_id": null
  }
}
✅ Trace context included: abc123def456...
=== END DEBUG ===
```

### In weather_fetcher logs:
```
=== DEBUG MESSAGE in weather_fetcher ===
{
  "zip_code": "78729",
  "scheduled_at": "2025-01-15T10:30:00Z",
  "_trace": {
    "trace_id": "abc123def456...",
    "span_id": "xyz789",
    "parent_span_id": null
  }
}
✅ Trace context found: abc123def456...
=== END DEBUG ===
🔍 Extracted trace_id: abc123def456...
```

## Common Issues

### If `_trace` is missing in weather_fetcher:

**Problem:** The `to_js()` conversion might be stripping the field

**Solution:** Check if you need to use a different serialization approach for Cloudflare queues

### If trace_id is None:

**Problem:** The extraction isn't finding the field

**Solution:** The message format might be different than expected. The debug output will show you the actual structure.

### If you see "❌ No _trace field in message!":

**Possible causes:**
1. The web worker code wasn't deployed
2. The message was sent before adding trace context
3. The queue is processing old messages

**Fix:** Wait a minute for old messages to clear, then trigger a new generation.

## Quick Test Command

Run this after deploying to see both logs:

```bash
# Trigger generation
curl -X POST "https://your-worker.workers.dev/admin/generate?zip=78729"

# Watch logs (in separate terminals)
wrangler tail weather-landscape-web
wrangler tail weather-fetcher
```

Look for the trace_id in both logs to confirm propagation is working!
