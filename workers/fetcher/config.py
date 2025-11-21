"""
Configuration for Weather Fetcher Worker - Minimal version
"""

from js import Object
from pyodide.ffi import to_js as _to_js


def to_js(obj):
    """Convert Python dict to JavaScript object for Response headers"""
    return _to_js(obj, dict_converter=Object.fromEntries)


# Format configuration mapping (needed by kv_utils)
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


class WorkerConfig:
    """Minimal configuration for Weather Fetcher Worker"""
    def __init__(self, env):
        # Access environment variables directly from env object
        try:
            self.OWM_KEY = getattr(env, 'OWM_API_KEY', None)
        except Exception:
            self.OWM_KEY = None

        try:
            self.ZIP_CODE = str(getattr(env, 'DEFAULT_ZIP', '78729'))
        except Exception:
            self.ZIP_CODE = '78729'
