import os

from .p_weather.openweathermap import OpenWeatherMap
from .p_weather.draw_weather import DrawWeather
from .p_weather.configuration import WLBaseSettings

import secrets


class WeatherLandscape:


    def __init__(self,configuration:WLBaseSettings, require_api_key=True):
        self.cfg = WLBaseSettings.Fill( configuration, secrets )
        if require_api_key:
            assert self.cfg.OWM_KEY != "000000000000000000",  "Set OWM_KEY variable to your OpenWeather API key in secrets.py"


    async def MakeImage(self):
        """Generate weather landscape image (async for Cloudflare Workers)"""
        # Import PIL at runtime for Cloudflare Workers compatibility
        from PIL import Image
        import io
        import os
        from asset_loader import get_global_loader

        owm = OpenWeatherMap(self.cfg)
        await owm.FromAuto()

        # Load the template image using the asset loader
        try:
            loader = get_global_loader()
            # Use template from config (handles different formats)
            # Strip leading path components for asset loader
            template_path = self.cfg.TEMPLATE_FILENAME
            if template_path.startswith('src/'):
                template_path = template_path[4:]

            # Get the buffer data using asset loader
            buffer_data = loader.load_asset(template_path)

            img = Image.open(io.BytesIO(buffer_data))
        except Exception as e:
            print(f"Error loading template buffer: {e}")
            # Fallback for local development
            img = Image.open(self.cfg.TEMPLATE_FILENAME)

        art = DrawWeather(img,self.cfg)
        img = art.Draw(owm)

        return img

    async def MakeImageFromData(self, weather_data):
        """
        Generate weather landscape image from pre-fetched weather data

        Args:
            weather_data: Dict containing 'current' and 'forecast' keys
                         with raw OpenWeatherMap API responses

        Returns:
            PIL Image object
        """
        # Import PIL at runtime for Cloudflare Workers compatibility
        from PIL import Image
        import io
        from asset_loader import get_global_loader

        owm = OpenWeatherMap(self.cfg)

        # Load from pre-fetched data instead of making API calls
        owm.FromJSON(weather_data['current'], weather_data['forecast'])

        # Load the template image using the asset loader
        try:
            loader = get_global_loader()
            # Use template from config (handles different formats)
            # Strip leading path components for asset loader
            template_path = self.cfg.TEMPLATE_FILENAME
            if template_path.startswith('src/'):
                template_path = template_path[4:]

            # Get the buffer data using asset loader
            buffer_data = loader.load_asset(template_path)

            img = Image.open(io.BytesIO(buffer_data))
        except Exception as e:
            print(f"Error loading template buffer: {e}")
            # Fallback for local development
            img = Image.open(self.cfg.TEMPLATE_FILENAME)

        art = DrawWeather(img, self.cfg)
        img = art.Draw(owm)

        return img

    async def SaveImage(self,suffix:str=None)->str:
        """Save generated image to file (async-aware)"""
        img = await self.MakeImage()
        outfilepath = self.cfg.ImageFilePath(suffix)
        img.save(outfilepath)
        return outfilepath
        

        