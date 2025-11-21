"""
Minimal utilities for the web worker - serving HTML/CSS and managing KV/R2
"""

import json
import os
from js import Object
from pyodide.ffi import to_js as _to_js
from string import Template


def to_js(obj):
    """Convert Python dict to JavaScript object for Response headers"""
    return _to_js(obj, dict_converter=Object.fromEntries)


def load_template(template_name):
    """Load an HTML template file"""
    workers_dir = os.path.dirname(__file__)
    template_path = os.path.join(workers_dir, 'assets', 'templates', template_name)
    with open(template_path, 'r') as f:
        return f.read()


def render_template(template_name, **context):
    """Render a template with $variable substitution (string.Template)"""
    template_str = load_template(template_name)
    template = Template(template_str)
    return template.substitute(**context)


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


# === KV Utilities ===

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


async def add_format_to_zip(env, zip_code, format_name):
    """
    Add a format to be generated for a specific ZIP code

    Args:
        env: Worker environment
        zip_code: ZIP code
        format_name: Format to add (e.g., 'rgb_dark', 'bw')

    Returns:
        list: Updated list of formats for this ZIP
    """
    if format_name not in FORMAT_CONFIGS:
        raise ValueError(f"Unknown format: {format_name}")

    formats = await get_formats_for_zip(env, zip_code)
    if format_name not in formats:
        formats.append(format_name)
        kv_key = f"formats:{zip_code}"
        await env.CONFIG.put(kv_key, json.dumps(formats))
        print(f"Added format {format_name} to {zip_code}")
    return formats


async def remove_format_from_zip(env, zip_code, format_name):
    """
    Remove a format from being generated for a specific ZIP code

    Args:
        env: Worker environment
        zip_code: ZIP code
        format_name: Format to remove

    Returns:
        list: Updated list of formats for this ZIP
    """
    if format_name == DEFAULT_FORMAT:
        raise ValueError(f"Cannot remove default format {DEFAULT_FORMAT}")

    formats = await get_formats_for_zip(env, zip_code)
    if format_name in formats:
        formats.remove(format_name)
        kv_key = f"formats:{zip_code}"
        await env.CONFIG.put(kv_key, json.dumps(formats))
        print(f"Removed format {format_name} from {zip_code}")
    return formats


async def add_zip_to_active(env, zip_code):
    """
    Add a ZIP code to the active_zips list

    Args:
        env: Worker environment
        zip_code: ZIP code to add

    Returns:
        list: Updated list of active ZIP codes
    """
    try:
        active_zips = await get_active_zips(env)
        if zip_code not in active_zips:
            active_zips.append(zip_code)
            await env.CONFIG.put('active_zips', json.dumps(active_zips))
            print(f"Added {zip_code} to active_zips")
        return active_zips
    except Exception as e:
        print(f"Error adding {zip_code} to active_zips: {e}")
        raise


async def get_all_zips_from_r2(env):
    """
    Scan R2 bucket to find all ZIP codes that have images

    Returns:
        list: List of ZIP code strings found in R2
    """
    try:
        if env is None:
            print("ERROR: env is None in get_all_zips_from_r2")
            return []

        if not hasattr(env, 'WEATHER_IMAGES'):
            print(f"ERROR: env has no WEATHER_IMAGES binding. env type: {type(env)}, attrs: {dir(env)}")
            return []

        zip_codes = set()

        # List all objects in the R2 bucket
        # R2 list() returns objects with keys like "78729/rgb_light.png"
        listed = await env.WEATHER_IMAGES.list()

        # Extract ZIP codes from object keys
        if hasattr(listed, 'objects'):
            for obj in listed.objects:
                # Object key format: "78729/rgb_light.png"
                key = obj.key
                if '/' in key:
                    zip_code = key.split('/')[0]
                    # Validate it looks like a ZIP code (5 digits)
                    if zip_code.isdigit() and len(zip_code) == 5:
                        zip_codes.add(zip_code)

        return sorted(list(zip_codes))
    except Exception as e:
        print(f"Warning: Failed to list R2 objects: {e}")
        return []


async def get_formats_per_zip(env):
    """
    Scan R2 bucket to find which formats are available for each ZIP

    Returns:
        dict: {zip_code: [format_names]}
    """
    try:
        zip_formats = {}

        # List all objects in the R2 bucket
        listed = await env.WEATHER_IMAGES.list()

        # Extract ZIP codes and formats from object keys
        if hasattr(listed, 'objects'):
            for obj in listed.objects:
                # Object key format: "78729/rgb_light.png" or "78729/bw.bmp"
                key = obj.key
                if '/' in key:
                    parts = key.split('/')
                    zip_code = parts[0]
                    if zip_code.isdigit() and len(zip_code) == 5 and len(parts) > 1:
                        # Extract format from filename (remove extension)
                        filename = parts[1]
                        format_name = filename.rsplit('.', 1)[0] if '.' in filename else filename

                        # Check if it's a valid format
                        if format_name in FORMAT_CONFIGS:
                            if zip_code not in zip_formats:
                                zip_formats[zip_code] = []
                            if format_name not in zip_formats[zip_code]:
                                zip_formats[zip_code].append(format_name)

        # Sort formats for each ZIP (default first, then alphabetical)
        for zip_code in zip_formats:
            formats = zip_formats[zip_code]
            # Sort with default format first
            sorted_formats = []
            if DEFAULT_FORMAT in formats:
                sorted_formats.append(DEFAULT_FORMAT)
            for fmt in sorted(formats):
                if fmt != DEFAULT_FORMAT:
                    sorted_formats.append(fmt)
            zip_formats[zip_code] = sorted_formats

        return zip_formats
    except Exception as e:
        print(f"Warning: Failed to get formats per zip: {e}")
        return {}
