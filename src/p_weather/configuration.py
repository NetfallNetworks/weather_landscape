import os
from p_weather.holidays import WLHolidays,WLHEntry
import datetime
from typing import List,Tuple



class WLBaseSettings(object):

    SPRITES_MODE_BW = 0
    SPRITES_MODE_RGB = 1
    
    

    TEMP_UNITS_CELSIUS = 0 
    TEMP_UNITS_FAHRENHEIT = 1
    PRESSURE_RAIN_HPA = 980
    PRESSURE_FAIR_HPA = 1040

    @property
    def IsCelsius(self):
        return self.TEMPUNITS_MODE!=self.TEMP_UNITS_FAHRENHEIT

    TITLE = "Base config"
    OWM_KEY = "000000000000000000" 
    OWM_LAT = 52.196136
    OWM_LON = 21.007963
    TEMPUNITS_MODE = 0
    PRESSURE_MIN = 980
    PRESSURE_MAX = 1030
    WORK_DIR = None
    OUT_FILENAME = "landscape"
    OUT_FILEEXT = ".bmp"
    TEMPLATE_FILENAME = "template.bmp"
    SPRITES_DIR="sprite"

    POSTPROCESS_INVERT = False
    POSTPROCESS_EINKFLIP = False      
    SPRITES_MODE = SPRITES_MODE_BW

    COLOR_SOIL = (0,0,0)
    COLOR_SMOKE = (127,127,127) 
    COLOR_BG = (255,255,255)
    COLOR_FG = (0,0,0)    
    COLOR_RAIN = (0,0,255)
    COLOR_SNOW = (255,255,255)

    
    
    @staticmethod
    def Fill(cfg,obj):
        print("Settings:")
        for key in obj.__dict__.keys():
            if not key.startswith('__'):
                if key.upper() == key:
                    val = obj.__dict__[key]
                    setattr(cfg, key, val)
                    if (key=='OWM_KEY'):
                        print('  ','OWM_KEY updated')
                    else:
                        print('  ',key,'=',val)
                else:
                    print('  ',key,'ignored')
        return cfg 

        
    DRAWOFFSET = 65    
    DRAW_XSTART = 32
    DRAW_XSTEP  = 44
    DRAW_XFLAT =  10
    DRAW_YSTEP = 50  #64
    DRAW_DEFAULT_DEGREE_PER_PIXEL = 0.5
    DRAW_FLOWER_RIGHT_PX = 15
    DRAW_FLOWER_LEFT_PX = 10
    
    
    # Temperature units
    # 0 - Celsius
    # 1 - Fahrenheit
    TEMPUNITS_MODE = 0


    # High and low pressure values in hPa for smoke visualization
    PRESSURE_MIN = 980
    PRESSURE_MAX = 1030    

    
    def ImageFilePath(self,suffix:str=None):
        if suffix==None:
            suffix=''
        return self.MakeFilePath(self.OUT_FILENAME+suffix+self.OUT_FILEEXT)

    def MakeFilePath(self,filename):
        return os.path.join(self.WORK_DIR,filename)                
        
        
    MIMES = {
            '.gif': 'image/gif',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.bmp': 'image/bmp',
        }  

    def GetMIME(self):
        return self.MIMES.get(self.OUT_FILEEXT.lower(), None)        
    
    
    HOLIDAYS = WLHolidays()
    
    def LoadHolidays(self,path:str=None):
        return self.HOLIDAYS.Load(path)
        
        
    def GetAllHolidays(self, t0 : datetime.datetime, t1: datetime.datetime) -> List[WLHEntry]:
        return self.HOLIDAYS.GetAll(t0,t1)