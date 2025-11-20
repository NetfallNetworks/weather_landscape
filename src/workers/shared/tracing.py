"""
Distributed Tracing Utilities

Provides trace ID generation and propagation across workers and queues
for end-to-end request tracing.
"""

import uuid
import json


def generate_trace_id():
    """
    Generate a unique trace ID for tracking requests across workers.

    Returns:
        str: A unique trace ID (UUID4 format without hyphens)
    """
    return uuid.uuid4().hex


def add_trace_context(message_dict, trace_id=None, parent_span_id=None):
    """
    Add trace context to a queue message.

    Args:
        message_dict: The message dictionary to add trace context to
        trace_id: Optional trace ID (generates new one if not provided)
        parent_span_id: Optional parent span ID for nested spans

    Returns:
        dict: Message with trace context added
    """
    if trace_id is None:
        trace_id = generate_trace_id()

    message_dict['_trace'] = {
        'trace_id': trace_id,
        'span_id': uuid.uuid4().hex[:16],  # Shorter span ID
        'parent_span_id': parent_span_id
    }

    return message_dict


def extract_trace_context(message):
    """
    Extract trace context from a queue message.

    Args:
        message: The queue message (can be dict or object with .body)

    Returns:
        dict: Trace context with trace_id, span_id, parent_span_id
              Returns None if no trace context found
    """
    try:
        # Handle different message formats
        if isinstance(message, dict):
            body = message
        elif hasattr(message, 'body'):
            body = message.body if isinstance(message.body, dict) else json.loads(message.body)
        else:
            return None

        return body.get('_trace')
    except Exception:
        return None


def log_with_trace(message, trace_context=None, **extra_fields):
    """
    Log a message with trace context for correlation.

    Args:
        message: The log message
        trace_context: Trace context dict from extract_trace_context()
        **extra_fields: Additional fields to include in the log
    """
    log_data = {
        'message': message,
        **extra_fields
    }

    if trace_context:
        log_data['trace_id'] = trace_context.get('trace_id')
        log_data['span_id'] = trace_context.get('span_id')
        log_data['parent_span_id'] = trace_context.get('parent_span_id')

    # Print as JSON for structured logging
    print(json.dumps(log_data))


def get_trace_id(trace_context):
    """
    Get just the trace_id from trace context (convenience function).

    Args:
        trace_context: Trace context dict

    Returns:
        str: Trace ID or None
    """
    return trace_context.get('trace_id') if trace_context else None
