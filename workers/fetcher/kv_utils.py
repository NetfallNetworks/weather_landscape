"""
KV Store utilities for Weather Fetcher Worker - Minimal version
Only includes functions needed for fetching and storing weather data
"""

import json
from datetime import datetime
from js import fetch

from config import FORMAT_CONFIGS, DEFAULT_FORMAT


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
