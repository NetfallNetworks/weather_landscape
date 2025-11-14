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

        owm = OpenWeatherMap(self.cfg)
        await owm.FromAuto()

        # In Cloudflare Workers, bundled buffer files need special access
        try:
            # Try importing the buffer via __loader__
            import sys
            loader = sys.modules['__main__'].__loader__

            # The bundled path from deployment output
            buffer_path = 'p_weather/template_rgb.bmp'
            print(f"DEBUG: Trying to load buffer: {buffer_path}")

            # Get the buffer data
            buffer_data = loader.get_data(buffer_path)
            print(f"DEBUG: Loaded buffer, size: {len(buffer_data)} bytes")

            img = Image.open(io.BytesIO(buffer_data))
        except Exception as e:
            print(f"DEBUG: Buffer loading failed: {e}")
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
        

        