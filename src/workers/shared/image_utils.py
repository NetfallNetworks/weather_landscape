"""
Image generation utilities for Weather Landscape workers
"""

from datetime import datetime
from .config import FORMAT_CONFIGS, DEFAULT_FORMAT, WorkerConfig


async def generate_weather_image(env, zip_code, lat, lon, format_name=None, weather_data=None):
    """
    Generate a weather landscape image using current weather data

    Args:
        env: Worker environment
        zip_code: ZIP code for this generation
        lat: Latitude for weather lookup
        lon: Longitude for weather lookup
        format_name: Format to generate (e.g., 'rgb_white', 'bw', 'eink')
        weather_data: Pre-fetched weather data (optional, if not provided will fetch)

    Returns:
        tuple: (image_bytes, metadata_dict, format_name)
    """
    try:
        # Import at runtime (Pillow loaded from cf-requirements.txt)
        from weather_landscape import WeatherLandscape
        from asset_loader import set_global_loader
        import io

        # Initialize the global asset loader
        set_global_loader()

        # Load configuration from environment
        config = WorkerConfig(env)

        # Check for API key
        if not config.OWM_KEY:
            raise ValueError("OWM_API_KEY not set in environment")

        # Default to DEFAULT_FORMAT if not specified
        if format_name is None:
            format_name = DEFAULT_FORMAT

        # Get format info
        format_info = FORMAT_CONFIGS.get(format_name)
        if not format_info:
            raise ValueError(f"Unknown format: {format_name}")

        # Generate the image with provided lat/lon and format
        weather_config = config.to_weather_config(lat=lat, lon=lon, format_name=format_name)

        # Debug: Log which config class and colors are being used
        print(f"Config for {format_name}: {weather_config.__class__.__name__}")
        if hasattr(weather_config, 'COLOR_BG'):
            print(f"   COLOR_BG: {weather_config.COLOR_BG}")
        if hasattr(weather_config, 'COLOR_FG'):
            print(f"   COLOR_FG: {weather_config.COLOR_FG}")
        print(f"   TEMPLATE: {weather_config.TEMPLATE_FILENAME}")
        print(f"   SPRITES_MODE: {weather_config.SPRITES_MODE}")

        wl = WeatherLandscape(weather_config)

        # If weather data is provided, use it instead of fetching
        if weather_data:
            img = await wl.MakeImageFromData(weather_data)
        else:
            img = await wl.MakeImage()

        # Convert PIL Image to bytes
        buffer = io.BytesIO()
        # Determine save format based on extension
        save_format = 'PNG' if format_info['extension'] == '.png' else 'BMP'
        img.save(buffer, format=save_format)
        image_bytes = buffer.getvalue()

        # Create metadata
        metadata = {
            'generatedAt': datetime.utcnow().isoformat() + 'Z',
            'latitude': lat,
            'longitude': lon,
            'zipCode': zip_code,
            'fileSize': len(image_bytes),
            'format': save_format,
            'variant': format_name
        }

        return image_bytes, metadata, format_name

    except Exception as e:
        print(f"Error generating {format_name} image for {zip_code}: {e}")
        raise


async def generate_weather_image_from_kv(env, zip_code, format_name=None):
    """
    Generate a weather landscape image using weather data from KV

    This function is used by the landscape-generator worker to generate
    images from cached weather data.

    Args:
        env: Worker environment
        zip_code: ZIP code for this generation
        format_name: Format to generate (e.g., 'rgb_white', 'bw', 'eink')

    Returns:
        tuple: (image_bytes, metadata_dict, format_name)
    """
    from .kv_utils import get_weather_data, geocode_zip
    from .config import WorkerConfig

    # Get cached weather data
    weather_data = await get_weather_data(env, zip_code)
    if not weather_data:
        raise ValueError(f"No weather data found for {zip_code}")

    # Get geo data for lat/lon
    config = WorkerConfig(env)
    geo_data = await geocode_zip(env, zip_code, config.OWM_KEY)

    # Generate image using cached weather data
    return await generate_weather_image(
        env,
        zip_code,
        geo_data['lat'],
        geo_data['lon'],
        format_name,
        weather_data
    )
