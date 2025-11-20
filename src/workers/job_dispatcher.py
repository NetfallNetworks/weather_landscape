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
from js import JSON


from shared import (
    get_formats_for_zip,
    to_js,
    extract_trace_context,
    add_trace_context,
    log_with_trace,
    get_trace_id
)


class Default(WorkerEntrypoint):
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
        env = self.env

        print(f"Job Dispatcher received {len(batch.messages)} event(s)")

        total_jobs = 0

        for message in batch.messages:
            try:
                # Parse event data (convert JsProxy via JSON round-trip)
                event = json.loads(JSON.stringify(message.body))

                zip_code = event['zip_code']
                lat = event['lat']
                lon = event['lon']

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

                # Acknowledge the message
                message.ack()

            except Exception as e:
                log_with_trace(
                    f"ERROR dispatching jobs: {e}",
                    trace_context=trace_context if 'trace_context' in locals() else None,
                    error=str(e),
                    worker='job_dispatcher',
                    action='error'
                )
                message.retry()

        print(f"Job Dispatcher completed: {total_jobs} jobs enqueued")


# Export the worker class
