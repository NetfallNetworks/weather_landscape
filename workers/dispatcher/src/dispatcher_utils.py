"""
Utilities for Job Dispatcher Worker - Minimal version

Only includes functions needed by the dispatcher:
- get_formats_for_zip(): Look up configured formats from KV
- to_js(): Convert Python objects to JavaScript
- FORMAT_CONFIGS and DEFAULT_FORMAT: Format configuration constants
"""

import json
from js import Object
from pyodide.ffi import to_js as _to_js


def to_js(obj):
    """Convert Python dict to JavaScript object"""
    return _to_js(obj, dict_converter=Object.fromEntries)


# Format configuration mapping
FORMAT_CONFIGS = {
    'rgb_light': {
        'class_name': 'WLConfig_RGB_White',
        'extension': '.png',
        'mime_type': 'image/png',
        'title': 'RGB Light Theme'
    },
    'rgb_dark': {
        'class_name': 'WLConfig_RGB_Black',
        'extension': '.png',
        'mime_type': 'image/png',
        'title': 'RGB Dark Theme'
    },
    'bw': {
        'class_name': 'WLConfig_BW',
        'extension': '.bmp',
        'mime_type': 'image/bmp',
        'title': 'Black & White'
    },
    'eink': {
        'class_name': 'WLConfig_EINK',
        'extension': '.bmp',
        'mime_type': 'image/bmp',
        'title': 'E-Ink (Flipped)'
    },
    'bwi': {
        'class_name': 'WLConfig_BWI',
        'extension': '.bmp',
        'mime_type': 'image/bmp',
        'title': 'Black & White Inverted'
    }
}

# Default format (always generated)
DEFAULT_FORMAT = 'rgb_light'


async def get_formats_for_zip(env, zip_code):
    """
    Get list of formats to generate for a specific ZIP code from KV

    Args:
        env: Worker environment
        zip_code: ZIP code

    Returns:
        list: Format names (always includes DEFAULT_FORMAT)
    """
    try:
        kv_key = f"formats:{zip_code}"
        formats_json = await env.CONFIG.get(kv_key)
        if formats_json:
            formats = json.loads(formats_json)
            # Ensure default format is always included
            if DEFAULT_FORMAT not in formats:
                formats.insert(0, DEFAULT_FORMAT)
            return formats
        else:
            # No config for this ZIP, use default only
            return [DEFAULT_FORMAT]
    except Exception as e:
        print(f"Warning: Failed to get formats for {zip_code}: {e}")
        return [DEFAULT_FORMAT]
