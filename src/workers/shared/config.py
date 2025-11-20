"""
Configuration and format definitions for Weather Landscape workers
"""

from js import Object
from pyodide.ffi import to_js as _to_js
from string import Template
import os


def to_js(obj):
    """Convert Python dict to JavaScript object for Response headers"""
    return _to_js(obj, dict_converter=Object.fromEntries)


def load_template(template_name):
    """Load an HTML template file"""
    # Navigate from shared/ to templates/
    src_dir = os.path.dirname(os.path.dirname(__file__))
    template_dir = os.path.join(src_dir, 'templates')
    path = os.path.join(template_dir, template_name)
    with open(path, 'r') as f:
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


class WorkerConfig:
    """Configuration loaded from KV and environment"""
    def __init__(self, env):
        # Access environment variables directly from env object
        # Secrets (like OWM_API_KEY) are set via: wrangler secret put OWM_API_KEY
        # Vars (like DEFAULT_ZIP) are set in wrangler.toml [vars] section
        try:
            self.OWM_KEY = getattr(env, 'OWM_API_KEY', None)
        except Exception as e:
            self.OWM_KEY = None

        try:
            self.ZIP_CODE = str(getattr(env, 'DEFAULT_ZIP', '78729'))
        except:
            self.ZIP_CODE = '78729'

        self.WORK_DIR = "/tmp"

    def to_weather_config(self, lat, lon, format_name=None):
        """
        Convert to WeatherLandscape config format

        Args:
            lat: Latitude (required)
            lon: Longitude (required)
            format_name: Format name (e.g., 'rgb_white', 'bw', 'eink')
        """
        # Import at runtime to allow Pillow to load first
        from . import configs

        # Default to RGB_White if no format specified
        if format_name is None:
            format_name = DEFAULT_FORMAT

        # Get config class for this format
        format_info = FORMAT_CONFIGS.get(format_name)
        if not format_info:
            raise ValueError(f"Unknown format: {format_name}")

        # Get the config class dynamically
        config_class = getattr(configs, format_info['class_name'])
        config = config_class()

        config.OWM_KEY = self.OWM_KEY
        config.OWM_LAT = lat
        config.OWM_LON = lon
        config.WORK_DIR = self.WORK_DIR
        return config
