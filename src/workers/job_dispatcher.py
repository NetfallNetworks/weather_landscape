"""
Job Dispatcher Worker

Queue consumer that creates the fan-out from weather-ready events:
1. Consumes "weather ready" events
2. Looks up configured formats for each ZIP
3. Enqueues individual generation jobs
"""

import json
from datetime import datetime
from workers import WorkerEntrypoint

from .shared import get_formats_for_zip


class JobDispatcher(WorkerEntrypoint):
    """
    Job Dispatcher Worker
    Fans out weather-ready events into individual generation jobs
    """

    async def queue(self, batch, env, ctx):
        """
        Queue consumer handler - processes weather-ready events

        Args:
            batch: Batch of messages from the weather-ready queue
            env: Worker environment
            ctx: Execution context
        """
        print(f"Job Dispatcher received {len(batch.messages)} event(s)")

        total_jobs = 0

        for message in batch.messages:
            try:
                # Parse event data
                event = message.body

                zip_code = event['zip_code']
                lat = event['lat']
                lon = event['lon']

                print(f"Processing weather-ready for {zip_code}")

                # Get formats configured for this ZIP
                formats = await get_formats_for_zip(env, zip_code)
                print(f"  Dispatching {len(formats)} job(s): {', '.join(formats)}")

                # Enqueue a job for each format
                for format_name in formats:
                    job = {
                        'zip_code': zip_code,
                        'format_name': format_name,
                        'lat': lat,
                        'lon': lon,
                        'enqueued_at': datetime.utcnow().isoformat() + 'Z'
                    }

                    await env.LANDSCAPE_JOBS.send(job)
                    total_jobs += 1

                # Acknowledge the message
                message.ack()

            except Exception as e:
                print(f"ERROR dispatching jobs: {e}")
                message.retry()

        print(f"Job Dispatcher completed: {total_jobs} jobs enqueued")


# Export the worker class
export = JobDispatcher
