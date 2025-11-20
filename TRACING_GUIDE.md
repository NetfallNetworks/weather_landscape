# End-to-End Distributed Tracing Guide

This guide shows how to implement distributed tracing across your worker pipeline to track requests from the admin UI all the way through to final image generation.

## Overview

Your pipeline flow:
```
Admin UI (web.py)
    ↓ [FETCH_JOBS queue]
Weather Fetcher (weather_fetcher.py)
    ↓ [WEATHER_READY queue]
Job Dispatcher (job_dispatcher.py)
    ↓ [LANDSCAPE_JOBS queue]
Landscape Generator (landscape_generator.py)
```

With distributed tracing, each request gets a unique `trace_id` that flows through all workers and queues.

## How It Works

1. **Generate trace_id**: When a request enters (e.g., `POST /admin/generate`), generate a unique trace ID
2. **Propagate through queues**: Add trace context to every queue message
3. **Log consistently**: Each worker logs with the trace ID
4. **Correlate in dashboard**: Search Cloudflare traces by trace_id to see the entire request flow

## Implementation

### 1. Update `web.py` - Generate Trace ID

In your `_handle_generate` method (around line 669):

```python
from shared.tracing import generate_trace_id, add_trace_context, log_with_trace

async def _handle_generate(self, env, query_params):
    """
    Handle POST /admin/generate
    Enqueues ZIP to fetch-jobs queue for processing through the pipeline
    """
    try:
        zip_code = query_params.get('zip')
        if not zip_code or not (zip_code.isdigit() and len(zip_code) == 5):
            return Response.new(
                json.dumps({'error': 'Invalid ZIP code. Must be 5 digits.'}),
                {'status': 400, 'headers': {'Content-Type': 'application/json'}}
            )

        # Generate trace ID for end-to-end tracking
        trace_id = generate_trace_id()

        # Enqueue to fetch-jobs (weather-fetcher will handle the rest)
        job = {
            'zip_code': zip_code,
            'scheduled_at': datetime.utcnow().isoformat() + 'Z'
        }

        # Add trace context
        job = add_trace_context(job, trace_id=trace_id)

        # Log with trace context
        log_with_trace(
            f"Enqueuing generation for ZIP {zip_code}",
            trace_context=job['_trace'],
            zip_code=zip_code,
            worker='web',
            action='enqueue_fetch_job'
        )

        await env.FETCH_JOBS.send(to_js(job))

        return Response.new(
            json.dumps({
                'success': True,
                'zip': zip_code,
                'trace_id': trace_id,  # Return to client for tracking
                'message': f'Generation queued for ZIP {zip_code}'
            }),
            headers=to_js({'Content-Type': 'application/json'})
        )
    except Exception as e:
        # ... error handling
```

### 2. Update `weather_fetcher.py` - Propagate Trace ID

In your queue handler (around line 70):

```python
from shared.tracing import extract_trace_context, add_trace_context, log_with_trace, get_trace_id

async def queue(self, batch, env, ctx):
    """Queue consumer - processes fetch jobs"""
    success_count = 0
    error_count = 0

    for message in batch.messages:
        try:
            body = message.body
            zip_code = body['zip_code']

            # Extract trace context from incoming message
            trace_context = extract_trace_context(message)
            trace_id = get_trace_id(trace_context)

            log_with_trace(
                f"Fetching weather for ZIP {zip_code}",
                trace_context=trace_context,
                zip_code=zip_code,
                worker='weather_fetcher',
                action='fetch_weather'
            )

            # ... fetch weather data ...

            # Signal that weather is ready for this ZIP
            event_msg = {
                'zip_code': zip_code,
                'lat': geo_data['lat'],
                'lon': geo_data['lon'],
                'fetched_at': datetime.utcnow().isoformat() + 'Z'
            }

            # Propagate trace context to next queue
            event_msg = add_trace_context(
                event_msg,
                trace_id=trace_id,
                parent_span_id=trace_context['span_id'] if trace_context else None
            )

            log_with_trace(
                f"Weather ready for ZIP {zip_code}",
                trace_context=event_msg['_trace'],
                zip_code=zip_code,
                worker='weather_fetcher',
                action='weather_ready'
            )

            await env.WEATHER_READY.send(to_js(event_msg))

            message.ack()
            success_count += 1

        except Exception as e:
            error_count += 1
            log_with_trace(
                f"ERROR fetching weather: {e}",
                trace_context=trace_context,
                error=str(e),
                worker='weather_fetcher',
                action='error'
            )
            message.retry()

    print(f"Weather Fetcher completed: {success_count} success, {error_count} errors")
```

### 3. Update `job_dispatcher.py` - Continue Propagation

In your queue handler (around line 50):

```python
from shared.tracing import extract_trace_context, add_trace_context, log_with_trace, get_trace_id

async def queue(self, batch, env, ctx):
    """Queue consumer - receives weather-ready events"""
    total_jobs = 0

    for message in batch.messages:
        try:
            body = message.body
            zip_code = body['zip_code']
            lat = body['lat']
            lon = body['lon']

            # Extract trace context
            trace_context = extract_trace_context(message)
            trace_id = get_trace_id(trace_context)

            # Get formats configured for this ZIP
            formats = await get_formats_for_zip(env, zip_code)

            log_with_trace(
                f"Dispatching {len(formats)} jobs for ZIP {zip_code}",
                trace_context=trace_context,
                zip_code=zip_code,
                formats=formats,
                worker='job_dispatcher',
                action='dispatch_jobs'
            )

            # Enqueue a job for each format
            for format_name in formats:
                job = {
                    'zip_code': zip_code,
                    'format_name': format_name,
                    'lat': lat,
                    'lon': lon,
                    'enqueued_at': datetime.utcnow().isoformat() + 'Z'
                }

                # Propagate trace context
                job = add_trace_context(
                    job,
                    trace_id=trace_id,
                    parent_span_id=trace_context['span_id'] if trace_context else None
                )

                await env.LANDSCAPE_JOBS.send(to_js(job))
                total_jobs += 1

            message.ack()

        except Exception as e:
            log_with_trace(
                f"ERROR dispatching jobs: {e}",
                trace_context=trace_context,
                error=str(e),
                worker='job_dispatcher',
                action='error'
            )
            message.retry()

    print(f"Job Dispatcher completed: {total_jobs} jobs enqueued")
```

### 4. Update `landscape_generator.py` - Final Step

In your queue handler:

```python
from shared.tracing import extract_trace_context, log_with_trace

async def queue(self, batch, env, ctx):
    """Queue consumer - generates landscape images"""
    success_count = 0
    error_count = 0

    for message in batch.messages:
        try:
            body = message.body
            zip_code = body['zip_code']
            format_name = body.get('format_name', DEFAULT_FORMAT)

            # Extract trace context
            trace_context = extract_trace_context(message)

            log_with_trace(
                f"Generating {format_name} image for ZIP {zip_code}",
                trace_context=trace_context,
                zip_code=zip_code,
                format_name=format_name,
                worker='landscape_generator',
                action='generate_image'
            )

            # ... generate image ...

            log_with_trace(
                f"Successfully generated {format_name} for ZIP {zip_code}",
                trace_context=trace_context,
                zip_code=zip_code,
                format_name=format_name,
                worker='landscape_generator',
                action='generation_complete'
            )

            message.ack()
            success_count += 1

        except Exception as e:
            error_count += 1
            log_with_trace(
                f"ERROR generating image: {e}",
                trace_context=trace_context,
                error=str(e),
                worker='landscape_generator',
                action='error'
            )
            message.retry()
```

## Using Traces

### In Cloudflare Dashboard

1. Go to **Workers & Pages** → Select a worker → **Logs & Analytics** → **Traces**
2. Click on any trace to see logs
3. **Search by trace_id**: In the filter/search box, search for a specific trace_id
4. You'll see logs from all workers for that request!

### Example Log Output

With structured logging, each log entry will look like:
```json
{
  "message": "Generating rgb_dark image for ZIP 78729",
  "trace_id": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "span_id": "x1y2z3a4b5c6d7e8",
  "parent_span_id": "m9n8o7p6q5r4s3t2",
  "zip_code": "78729",
  "format_name": "rgb_dark",
  "worker": "landscape_generator",
  "action": "generate_image"
}
```

### Querying Traces

In Cloudflare Logpush or using Tail Workers, you can query by trace_id:
```bash
wrangler tail weather-landscape-web --format json | grep "a1b2c3d4e5f6"
```

## Benefits

✅ **End-to-end visibility**: Track a single request through the entire pipeline
✅ **Performance analysis**: See timing at each stage
✅ **Error debugging**: Find exactly where a request failed
✅ **Load analysis**: See which requests generate multiple jobs
✅ **Structured logging**: JSON format makes it easy to parse and analyze

## Advanced: Cloudflare Trace Context

Cloudflare Workers automatically add trace context headers. You can also use:
- `cf.traceId` - Cloudflare's internal trace ID
- Custom headers like `X-Request-ID` for external systems

To integrate with Cloudflare's native tracing, you can also use the `cf` object in requests.

## Next Steps

1. Add trace context to your workers (see examples above)
2. Deploy with `./deploy-all.sh`
3. Trigger a generation from admin UI
4. Copy the `trace_id` from the response
5. Search for that trace_id in Cloudflare dashboard to see the entire flow!
