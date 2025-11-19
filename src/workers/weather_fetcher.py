"""
Weather Fetcher Worker

Cron-triggered worker that:
1. Fetches weather data for all active ZIP codes
2. Stores weather data in KV
3. Enqueues image generation jobs to Cloudflare Queue
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
    get_formats_for_zip,
    store_weather_data,
    fetch_weather_from_owm
)


class WeatherFetcher(WorkerEntrypoint):
    """
    Weather Fetcher Worker
    Runs on cron schedule to fetch weather and enqueue generation jobs
    """

    async def scheduled(self, event, env, ctx):
        """
        Scheduled handler - runs on cron trigger (every 15 minutes)
        Fetches weather for all active ZIP codes and enqueues generation jobs
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
        jobs_enqueued = 0
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

                # Get formats configured for this ZIP
                enabled_formats = await get_formats_for_zip(env, zip_code)
                print(f"Enqueuing {len(enabled_formats)} job(s) for {zip_code}: {', '.join(enabled_formats)}")

                # Enqueue a job for each format
                for format_name in enabled_formats:
                    try:
                        # Create job message
                        job = {
                            'zip_code': zip_code,
                            'format_name': format_name,
                            'lat': geo_data['lat'],
                            'lon': geo_data['lon'],
                            'enqueued_at': datetime.utcnow().isoformat() + 'Z'
                        }

                        # Send to queue
                        await env.LANDSCAPE_JOBS.send(job)
                        jobs_enqueued += 1
                        print(f"  Enqueued: {zip_code}/{format_name}")

                    except Exception as e:
                        error_msg = f"Failed to enqueue {zip_code}/{format_name}: {str(e)}"
                        errors.append(error_msg)
                        print(f"  ERROR: {error_msg}")

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
                'jobsEnqueued': jobs_enqueued,
                'errors': errors if errors else None
            }
            await env.CONFIG.put('fetcher_status', json.dumps(status))
        except Exception as e:
            print(f"Warning: Failed to update fetcher status in KV: {e}")

        print(f"\nWeather Fetcher completed: {success_count} ZIPs processed, {jobs_enqueued} jobs enqueued, {error_count} errors")


# Export the worker class
export = WeatherFetcher
