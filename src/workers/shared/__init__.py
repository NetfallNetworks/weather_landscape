"""
Shared utilities for Weather Landscape workers
"""

from .config import (
    FORMAT_CONFIGS,
    DEFAULT_FORMAT,
    WorkerConfig,
    load_template,
    render_template,
    to_js
)

from .kv_utils import (
    geocode_zip,
    get_active_zips,
    get_formats_for_zip,
    add_format_to_zip,
    remove_format_from_zip,
    add_zip_to_active,
    get_all_zips_from_r2,
    get_formats_per_zip,
    get_weather_data,
    store_weather_data,
    fetch_weather_from_owm
)

from .r2_utils import upload_to_r2

from .image_utils import generate_weather_image

__all__ = [
    # Config
    'FORMAT_CONFIGS',
    'DEFAULT_FORMAT',
    'WorkerConfig',
    'load_template',
    'render_template',
    'to_js',
    # KV utils
    'geocode_zip',
    'get_active_zips',
    'get_formats_for_zip',
    'add_format_to_zip',
    'remove_format_from_zip',
    'add_zip_to_active',
    'get_all_zips_from_r2',
    'get_formats_per_zip',
    'get_weather_data',
    'store_weather_data',
    'fetch_weather_from_owm',
    # R2 utils
    'upload_to_r2',
    # Image utils
    'generate_weather_image'
]
