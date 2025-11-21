"""
Minimal utilities for landscape generator worker
Only includes functions actually used by the generator
"""

import json

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

DEFAULT_FORMAT = 'rgb_light'


class WorkerConfig:
    """Minimal configuration for landscape generator"""
    def __init__(self, env):
        # OWM_API_KEY not needed for generation (we use pre-fetched data)
        # but the WeatherLandscape class expects it to be set
        try:
            self.OWM_KEY = getattr(env, 'OWM_API_KEY', None)
        except:
            self.OWM_KEY = None

        self.WORK_DIR = "/tmp"

    def to_weather_config(self, lat, lon, format_name=None):
        """
        Convert to WeatherLandscape config format

        Args:
            lat: Latitude (required)
            lon: Longitude (required)
            format_name: Format name (e.g., 'rgb_light', 'bw', 'eink')
        """
        # Import at runtime to allow Pillow to load first
        import configs

        # Default to rgb_light if no format specified
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


async def get_weather_data(env, zip_code):
    """
    Retrieve weather data from KV

    Args:
        env: Worker environment
        zip_code: ZIP code

    Returns:
        dict: Weather data or None if not found/expired
    """
    kv_key = f"weather:{zip_code}"

    try:
        weather_json = await env.CONFIG.get(kv_key)
        if weather_json:
            return json.loads(weather_json)
        else:
            print(f"Warning: No weather data found for {zip_code}")
            return None
    except Exception as e:
        print(f"Error retrieving weather data for {zip_code}: {e}")
        return None


async def upload_to_r2(env, image_bytes, metadata, zip_code, format_name=None):
    """
    Upload generated image to R2 bucket

    Args:
        env: Worker environment
        image_bytes: Image bytes (PNG or BMP)
        metadata: Image metadata dict
        zip_code: ZIP code for folder organization
        format_name: Format name (e.g., 'rgb_light', 'bw')

    Returns:
        bool: True if successful
    """
    try:
        # Default to DEFAULT_FORMAT if not specified
        if format_name is None:
            format_name = DEFAULT_FORMAT

        # Get format info
        format_info = FORMAT_CONFIGS.get(format_name)
        if not format_info:
            raise ValueError(f"Unknown format: {format_name}")

        # Store ONE file per format: {zip}/{format}{ext}
        extension = format_info['extension']
        key = f"{zip_code}/{format_name}{extension}"

        # Prepare R2 metadata
        custom_metadata = {
            'generated-at': metadata['generatedAt'],
            'latitude': str(metadata['latitude']),
            'longitude': str(metadata['longitude']),
            'zip-code': zip_code,
            'file-size': str(metadata['fileSize']),
            'variant': format_name
        }

        # Convert Python bytes to JavaScript ArrayBuffer for R2
        # Use memoryview for efficient buffer protocol conversion
        from js import Uint8Array
        js_array = Uint8Array.new(memoryview(image_bytes))

        # Upload to R2 using ArrayBuffer (underlying buffer of Uint8Array)
        # Note: ~1.7s latency is due to geographic mismatch (worker in WNAM, bucket in ENAM)
        await env.WEATHER_IMAGES.put(
            key,
            js_array.buffer,
            {
                'httpMetadata': {
                    'contentType': format_info['mime_type'],
                },
                'customMetadata': custom_metadata
            }
        )

        print(f"Uploaded {key} to R2 ({len(image_bytes)} bytes)")

        # Save metadata to KV (per-ZIP-format)
        await env.CONFIG.put(
            f'metadata:{zip_code}:{format_name}',
            json.dumps(metadata)
        )

        return True

    except Exception as e:
        print(f"Error uploading {zip_code}/{format_name} to R2: {e}")
        raise
