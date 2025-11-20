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


from shared import (
    WorkerConfig,
    geocode_zip,
    store_weather_data,
    fetch_weather_from_owm
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
                # Parse job data (convert JsProxy to Python dict)
                job = message.body.to_py()
                zip_code = job['zip_code']

                print(f"Fetching weather for {zip_code}")

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

                await env.WEATHER_READY.send(event_msg)
                print(f"  Weather ready for {zip_code}")

                # Acknowledge the message
                message.ack()
                success_count += 1

            except Exception as e:
                error_count += 1
                print(f"ERROR fetching weather: {e}")
                message.retry()

        print(f"Weather Fetcher batch completed: {success_count} success, {error_count} errors")


# Export the worker class
