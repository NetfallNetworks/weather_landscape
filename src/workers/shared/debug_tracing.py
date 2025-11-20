"""
Debugging helper for distributed tracing

Add this to your workers temporarily to see what's in the queue messages
"""

import json
from js import JSON


def debug_message(message, worker_name="unknown"):
    """
    Print the full message body for debugging

    Args:
        message: Queue message
        worker_name: Name of the worker for context
    """
    try:
        # Parse the message body
        if hasattr(message, 'body'):
            body = json.loads(JSON.stringify(message.body))
        else:
            body = message

        print(f"=== DEBUG MESSAGE in {worker_name} ===")
        print(json.dumps(body, indent=2))
        print(f"=== END DEBUG ===")

        # Check for trace context
        if '_trace' in body:
            print(f"✅ Trace context found: {body['_trace'].get('trace_id')}")
        else:
            print(f"❌ No _trace field in message!")
            print(f"Available fields: {list(body.keys())}")

    except Exception as e:
        print(f"ERROR debugging message: {e}")


def debug_trace_propagation(job_dict, worker_name="unknown"):
    """
    Debug what's being sent to the next queue

    Args:
        job_dict: The dictionary being sent
        worker_name: Name of the worker sending it
    """
    print(f"=== DEBUG OUTGOING MESSAGE from {worker_name} ===")
    print(json.dumps(job_dict, indent=2, default=str))

    if '_trace' in job_dict:
        print(f"✅ Trace context included: {job_dict['_trace'].get('trace_id')}")
    else:
        print(f"❌ WARNING: No _trace field in outgoing message!")

    print(f"=== END DEBUG ===")
