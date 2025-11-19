"""
Weather Fetcher Worker

Cron-triggered worker that:
1. Fetches weather data for all active ZIP codes
2. Stores weather data in KV
3. Enqueues "weather ready" events for downstream processing
"""

import json
from datetime import datetime
from workers import WorkerEntrypoint

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from shared import (
    WorkerConfig,
    geocode_zip,
    get_active_zips,
    store_weather_data,
    fetch_weather_from_owm
)


class WeatherFetcher(WorkerEntrypoint):
    """
    Weather Fetcher Worker
    Runs on cron schedule to fetch weather and signal readiness
    """

    async def scheduled(self, event, env, ctx):
        """
        Scheduled handler - runs on cron trigger (every 15 minutes)
        Fetches weather for all active ZIP codes and signals readiness
        """
        print(f"Weather Fetcher started at {datetime.utcnow().isoformat()}")

        # Get configuration
        config = WorkerConfig(env)
        if not config.OWM_KEY:
            print("ERROR: OWM_API_KEY not set")
            return

        # Get active ZIP codes
        active_zips = await get_active_zips(env)
        print(f"Processing {len(active_zips)} ZIP code(s): {', '.join(active_zips)}")

        success_count = 0
        error_count = 0
        errors = []

        # Process each ZIP code
        for zip_code in active_zips:
            try:
                print(f"\nProcessing ZIP {zip_code}...")

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
                print(f"  Signaled weather ready for {zip_code}")

                success_count += 1

            except Exception as e:
                error_count += 1
                error_msg = f"ZIP {zip_code}: {str(e)}"
                errors.append(error_msg)
                print(f"ERROR processing {zip_code}: {e}")

        # Update overall status in KV
        try:
            status = {
                'lastFetchRun': datetime.utcnow().isoformat() + 'Z',
                'totalZips': len(active_zips),
                'successCount': success_count,
                'errorCount': error_count,
                'errors': errors if errors else None
            }
            await env.CONFIG.put('fetcher_status', json.dumps(status))
        except Exception as e:
            print(f"Warning: Failed to update fetcher status in KV: {e}")

        print(f"\nWeather Fetcher completed: {success_count} ZIPs processed, {error_count} errors")


# Export the worker class
export = WeatherFetcher
