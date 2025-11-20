"""
Weather Fetcher Worker

Queue consumer worker that:
1. Receives ZIP code from fetch-jobs queue
2. Fetches weather data from OpenWeatherMap
3. Stores weather data in KV
4. Enqueues "weather ready" event for downstream processing

Processes ONE ZIP per message for true parallelism.
"""

import json
from datetime import datetime
from workers import WorkerEntrypoint
from js import JSON


from shared import (
    WorkerConfig,
    geocode_zip,
    store_weather_data,
    fetch_weather_from_owm,
    to_js,
    extract_trace_context,
    add_trace_context,
    log_with_trace,
    get_trace_id,
    debug_message
)


class Default(WorkerEntrypoint):
    """
    Weather Fetcher Worker
    Consumes fetch-jobs queue and fetches weather for each ZIP
    """

    async def queue(self, batch, env, ctx):
        """
        Queue consumer handler - processes fetch jobs

        Args:
            batch: Batch of messages from the fetch-jobs queue
            env: Worker environment
            ctx: Execution context
        """
        env = self.env

        print(f"Weather Fetcher received {len(batch.messages)} job(s)")

        # Get configuration
        config = WorkerConfig(env)
        if not config.OWM_KEY:
            print("ERROR: OWM_API_KEY not set")
            # Retry all messages
            for message in batch.messages:
                message.retry()
            return

        success_count = 0
        error_count = 0

        for message in batch.messages:
            try:
                # DEBUG: Show what we received from the queue
                debug_message(message, worker_name="weather_fetcher")

                # Parse job data (convert JsProxy via JSON round-trip)
                job = json.loads(JSON.stringify(message.body))
                zip_code = job['zip_code']

                # Extract trace context from incoming message
                trace_context = extract_trace_context(message)
                trace_id = get_trace_id(trace_context)

                print(f"🔍 FETCHER: Extracted trace_id: {trace_id}")

                log_with_trace(
                    f"Fetching weather for ZIP {zip_code}",
                    trace_context=trace_context,
                    zip_code=zip_code,
                    worker='weather_fetcher',
                    action='fetch_weather'
                )

                # Geocode the ZIP (uses cache if available)
                geo_data = await geocode_zip(env, zip_code, config.OWM_KEY)

                # Fetch weather data from OpenWeatherMap
                weather_data = await fetch_weather_from_owm(
                    config.OWM_KEY,
                    geo_data['lat'],
                    geo_data['lon']
                )

                # Store weather data in KV with TTL
                await store_weather_data(env, zip_code, weather_data)

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

                # Acknowledge the message
                message.ack()
                success_count += 1

            except Exception as e:
                error_count += 1
                log_with_trace(
                    f"ERROR fetching weather: {e}",
                    trace_context=trace_context if 'trace_context' in locals() else None,
                    error=str(e),
                    worker='weather_fetcher',
                    action='error'
                )
                message.retry()

        print(f"Weather Fetcher batch completed: {success_count} success, {error_count} errors")


# Export the worker class
