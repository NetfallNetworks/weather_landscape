#!/usr/bin/env python
"""
Simple test script to verify local image generation works
"""

import sys

# Import from src/ directory
sys.path.insert(0, 'src')
from weather_landscape import WeatherLandscape
from configs import WLConfig_RGB_White

def main():
    print("Testing local weather landscape generation...")
    print()

    try:
        # Create configuration
        config = WLConfig_RGB_White()

        # Try to generate image
        print("Creating WeatherLandscape instance...")
        wl = WeatherLandscape(config)

        print("Generating image (this will fetch weather data)...")
        img = wl.MakeImage()

        # Save the image
        print("Saving image...")
        filepath = wl.SaveImage()

        print()
        print(f"✅ Success! Image generated at: {filepath}")
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
    main()
