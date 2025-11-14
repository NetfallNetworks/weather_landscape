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

        # In Cloudflare Workers, bundled files are in the same directory as the module
        try:
            # Try using module-relative path
            module_dir = os.path.dirname(os.path.abspath(__file__))
            template_path = os.path.join(module_dir, self.cfg.TEMPLATE_FILENAME)
            print(f"DEBUG: Trying template path: {template_path}")
            print(f"DEBUG: __file__ = {__file__}")
            print(f"DEBUG: module_dir = {module_dir}")
            print(f"DEBUG: Files in module_dir: {os.listdir(module_dir) if os.path.exists(module_dir) else 'DIR NOT EXISTS'}")

            with open(template_path, 'rb') as f:
                img = Image.open(io.BytesIO(f.read()))
        except Exception as e:
            print(f"DEBUG: Module-relative failed: {e}, trying config path directly")
            # Fallback: try config path directly
            try:
                with open(self.cfg.TEMPLATE_FILENAME, 'rb') as f:
                    img = Image.open(io.BytesIO(f.read()))
            except:
                # Final fallback for local development
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
        

        