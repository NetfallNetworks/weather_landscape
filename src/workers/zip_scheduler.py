"""
ZIP Scheduler Worker

Cron-triggered worker that:
1. Reads active ZIP codes from KV
2. Enqueues each ZIP to fetch-jobs queue for weather fetching

This is the entry point for the pipeline - very lightweight,
just schedules work without doing any actual processing.
"""

import json
from datetime import datetime
from workers import WorkerEntrypoint

from shared import get_active_zips


class ZipScheduler(WorkerEntrypoint):
    """
    ZIP Scheduler Worker
    Runs on cron schedule to enqueue ZIP codes for weather fetching
    """

    async def scheduled(self, controller, env, ctx):
        """
        Scheduled handler - runs on cron trigger (every 15 minutes)
        Enqueues all active ZIP codes for weather fetching
        """
        print(f"ZIP Scheduler started at {datetime.utcnow().isoformat()}")

        # Get active ZIP codes
        active_zips = await get_active_zips(env)
        print(f"Scheduling {len(active_zips)} ZIP code(s): {', '.join(active_zips)}")

        enqueued = 0

        # Enqueue each ZIP for weather fetching
        for zip_code in active_zips:
            try:
                job = {
                    'zip_code': zip_code,
                    'scheduled_at': datetime.utcnow().isoformat() + 'Z'
                }

                await env.FETCH_JOBS.send(job)
                enqueued += 1

            except Exception as e:
                print(f"ERROR enqueueing {zip_code}: {e}")

        # Update status in KV
        try:
            status = {
                'lastSchedulerRun': datetime.utcnow().isoformat() + 'Z',
                'totalZips': len(active_zips),
                'enqueued': enqueued
            }
            await env.CONFIG.put('scheduler_status', json.dumps(status))
        except Exception as e:
            print(f"Warning: Failed to update scheduler status: {e}")

        print(f"ZIP Scheduler completed: {enqueued} ZIPs enqueued")
