import os
from PIL import Image

from p_weather.openweathermap import OpenWeatherMap
from p_weather.draw_weather import DrawWeather
from p_weather.configuration import WLBaseSettings

import secrets


class WeatherLandscape:


    def __init__(self,configuration:WLBaseSettings):
        self.cfg = WLBaseSettings.Fill( configuration, secrets )    
        assert self.cfg.OWM_KEY != "000000000000000000",  "Set OWM_KEY variable to your OpenWeather API key in secrets.py"


    def MakeImage(self)->Image:

        owm = OpenWeatherMap(self.cfg)
        owm.FromAuto()

        img = Image.open(self.cfg.TEMPLATE_FILENAME)
        art = DrawWeather(img,self.cfg)
        img = art.Draw(owm)

        return img

    def SaveImage(self,suffix:str=None)->str:
        img = self.MakeImage() 
        outfilepath = self.cfg.ImageFilePath(suffix)
        img.save(outfilepath) 
        return outfilepath
        

        