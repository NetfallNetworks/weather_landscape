"""
KV Store utilities for Weather Landscape workers
"""

import json
from datetime import datetime
from js import fetch

from .config import FORMAT_CONFIGS, DEFAULT_FORMAT


async def geocode_zip(env, zip_code, api_key):
    """
    Geocode a ZIP code to lat/lon coordinates with KV caching

    Args:
        env: Worker environment (for KV access)
        zip_code: US ZIP code as string
        api_key: OpenWeatherMap API key

    Returns:
        dict: {'lat': float, 'lon': float, 'zip': str, 'cached_at': str}

    Raises:
        ValueError: If geocoding fails
    """
    kv_key = f"geo:{zip_code}"

    # Check KV cache first
    try:
        cached = await env.CONFIG.get(kv_key)
        if cached:
            geo_data = json.loads(cached)
            print(f"Using cached geocoding for {zip_code}: {geo_data['lat']}, {geo_data['lon']}")
            return geo_data
    except Exception as e:
        print(f"Warning: Failed to read geocoding cache for {zip_code}: {e}")

    # Not in cache, call OWM Geocoding API
    print(f"Geocoding ZIP {zip_code} via OWM API...")
    try:
        url = f"http://api.openweathermap.org/geo/1.0/zip?zip={zip_code},US&appid={api_key}"
        response = await fetch(url)

        if response.status != 200:
            raise ValueError(f"Geocoding API returned status {response.status}")

        data = await response.json()

        # Extract lat/lon from response
        geo_data = {
            'lat': float(data.lat),
            'lon': float(data.lon),
            'zip': zip_code,
            'cached_at': datetime.utcnow().isoformat() + 'Z'
        }

        # Store in KV cache (cache forever)
        try:
            await env.CONFIG.put(kv_key, json.dumps(geo_data))
            print(f"Cached geocoding for {zip_code}: {geo_data['lat']}, {geo_data['lon']}")
        except Exception as e:
            print(f"Warning: Failed to cache geocoding for {zip_code}: {e}")

        return geo_data

    except Exception as e:
        raise ValueError(f"Failed to geocode ZIP {zip_code}: {e}")


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


async def fetch_weather_from_owm(api_key, lat, lon):
    """
    Fetch weather data from OpenWeatherMap API

    Args:
        api_key: OpenWeatherMap API key
        lat: Latitude
        lon: Longitude

    Returns:
        dict: {'current': {...}, 'forecast': {...}} with raw API responses
    """
    OWMURL = "http://api.openweathermap.org/data/2.5/"
    reqstr = f"lat={lat:.4f}&lon={lon:.4f}&mode=json&APPID={api_key}"

    url_forecast = OWMURL + "forecast?" + reqstr
    url_current = OWMURL + "weather?" + reqstr

    # Fetch forecast data
    forecast_response = await fetch(url_forecast)
    if forecast_response.status != 200:
        raise ValueError(f"Forecast API returned status {forecast_response.status}")
    forecast_text = await forecast_response.text()
    import json as json_module
    forecast_data = json_module.loads(forecast_text)

    # Fetch current weather data
    current_response = await fetch(url_current)
    if current_response.status != 200:
        raise ValueError(f"Current weather API returned status {current_response.status}")
    current_text = await current_response.text()
    current_data = json_module.loads(current_text)

    print(f"Fetched weather for ({lat}, {lon})")

    return {
        'current': current_data,
        'forecast': forecast_data
    }


async def store_weather_data(env, zip_code, weather_data):
    """
    Store weather data in KV with TTL for later image generation

    Args:
        env: Worker environment
        zip_code: ZIP code
        weather_data: Weather data dict to store

    Returns:
        str: KV key where data was stored
    """
    kv_key = f"weather:{zip_code}"

    # Store with TTL of 20 minutes (longer than cron interval to allow for queue processing)
    expiration_ttl = 1200  # 20 minutes in seconds

    await env.CONFIG.put(
        kv_key,
        json.dumps(weather_data),
        {'expirationTtl': expiration_ttl}
    )

    print(f"Stored weather data for {zip_code} with TTL {expiration_ttl}s")
    return kv_key


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
