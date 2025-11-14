#!/usr/bin/env python
"""
Simple test script to verify local image generation works
Uses geocoding API like the deployed Cloudflare worker
"""

import sys
import asyncio
import aiohttp

# Import from src/ directory
sys.path.insert(0, 'src')
from weather_landscape import WeatherLandscape
from configs import WLConfig_RGB_White


async def geocode_zip(zip_code, api_key):
    """
    Geocode a US ZIP code to lat/lon using OpenWeatherMap API

    Args:
        zip_code: US ZIP code as string
        api_key: OpenWeatherMap API key

    Returns:
        tuple: (lat, lon)
    """
    url = f"http://api.openweathermap.org/geo/1.0/zip?zip={zip_code},US&appid={api_key}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise ValueError(f"Geocoding API returned status {response.status}")

            data = await response.json()
            return float(data['lat']), float(data['lon'])


async def main():
    print("Testing local weather landscape generation...")
    print()

    try:
        # Load secrets
        try:
            import secrets as user_secrets
            api_key = user_secrets.OWM_KEY
            zip_code = getattr(user_secrets, 'ZIP_CODE', '78729')
        except ImportError:
            print("❌ Error: secrets.py not found!")
            print()
            print("Please create secrets.py from secrets.py.example:")
            print("  cp secrets.py.example secrets.py")
            print("  # Then edit secrets.py and add your API key")
            print()
            sys.exit(1)

        # Validate API key
        if not api_key or api_key == "000000000000000000":
            raise AssertionError("API key not set")

        # Geocode ZIP code to lat/lon (like the deployed worker)
        print(f"Geocoding ZIP {zip_code}...")
        lat, lon = await geocode_zip(zip_code, api_key)
        print(f"  Coordinates: {lat}, {lon}")
        print()

        # Create configuration
        config = WLConfig_RGB_White()
        config.OWM_KEY = api_key
        config.OWM_LAT = lat
        config.OWM_LON = lon

        # Try to generate image
        print("Creating WeatherLandscape instance...")
        wl = WeatherLandscape(config)

        print("Generating image (this will fetch weather data)...")
        img = await wl.MakeImage()

        # Save the image
        print("Saving image...")
        filepath = await wl.SaveImage()

        print()
        print(f"✅ Success! Image generated at: {filepath}")
        print(f"   ZIP Code: {zip_code}")
        print(f"   Location: {lat}, {lon}")
        print(f"   Image size: {img.size}")
        print()
        print("You can now proceed with Cloudflare deployment!")

    except AssertionError as e:
        print()
        print("❌ Error: OpenWeather API key not set!")
        print()
        print("Please edit secrets.py and add your API key:")
        print("  OWM_KEY = 'your-actual-api-key-here'")
        print()
        print("Get a free key at: https://openweathermap.org/api")
        sys.exit(1)

    except Exception as e:
        print()
        print(f"❌ Error: {e}")
        print()
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
