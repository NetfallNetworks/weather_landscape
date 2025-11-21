"""
Minimal utilities for ZIP Scheduler Worker

This module contains ONLY the bare minimum dependencies needed by the
zip scheduler to avoid bundling unnecessary code like Pillow, image
generation, sprites, etc.

DO NOT import from shared/ here - that pulls in the entire kitchen sink!
"""

import json
from js import Object
from pyodide.ffi import to_js as _to_js


def to_js(obj):
    """Convert Python dict to JavaScript object for Response headers"""
    return _to_js(obj, dict_converter=Object.fromEntries)


async def get_active_zips(env):
    """
    Get list of active ZIP codes from KV

    Returns:
        list: List of ZIP code strings
    """
    try:
        active_zips_json = await env.CONFIG.get('active_zips')
        if active_zips_json:
            return json.loads(active_zips_json)
        else:
            # Initialize with default ZIP if not set
            default_zips = ['78729']
            await env.CONFIG.put('active_zips', json.dumps(default_zips))
            print(f"Initialized active_zips with default: {default_zips}")
            return default_zips
    except Exception as e:
        print(f"Warning: Failed to get active_zips from KV: {e}")
        return ['78729']  # Fallback to default
