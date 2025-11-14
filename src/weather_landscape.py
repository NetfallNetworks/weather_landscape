import os

from p_weather.openweathermap import OpenWeatherMap
from p_weather.draw_weather import DrawWeather
from p_weather.configuration import WLBaseSettings

import secrets


class WeatherLandscape:


    def __init__(self,configuration:WLBaseSettings):
        self.cfg = WLBaseSettings.Fill( configuration, secrets )
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
            buffer_path = 'p_weather/template_rgb.bmp'

            # Get the buffer data using asset loader
            buffer_data = loader.load_asset(buffer_path)

            img = Image.open(io.BytesIO(buffer_data))
        except Exception as e:
            print(f"Error loading template buffer: {e}")
            # Fallback for local development
            img = Image.open(self.cfg.TEMPLATE_FILENAME)

        art = DrawWeather(img,self.cfg)
        img = art.Draw(owm)

        return img

    async def SaveImage(self,suffix:str=None)->str:
        """Save generated image to file (async-aware)"""
        img = await self.MakeImage()
        outfilepath = self.cfg.ImageFilePath(suffix)
        img.save(outfilepath)
        return outfilepath
        

        