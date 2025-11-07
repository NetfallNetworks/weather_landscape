import os
from PIL import Image, ImageOps
import random
import math

from p_weather.configuration import WLBaseSettings
from p_weather.sprites import Sprites,Canvas





class SpritesRGB(Sprites):


    

    def __init__(self,config:WLBaseSettings,canvas:Image):
        super().__init__(config.SPRITES_DIR,canvas)
        self.cfg = config
        w, h = self.img.size 
        self.img.paste( self.cfg.COLOR_BG, (0, 0, w, h) )
        




    def Draw(self,name,index,xpos,ypos,ismirror=False):

        if (xpos<0) or (ypos<0):
            return 0
    
        img = self.GetSprite(name,index).convert('RGBA')
        if (ismirror):
            img = ImageOps.mirror(img)
        w, h = img.size            
            
        self.img.paste(img, (int(xpos),int(ypos)-h), img)            
            
        return w


    def DrawRain(self,value,xpos,ypos,width,tline):
        super().DrawRain(value,xpos,ypos,width,tline,self.cfg.COLOR_RAIN)
        



    def DrawSoil(self,tline:list[int],xoffset =0):
        super().DrawSoil(tline,xoffset,self.cfg.COLOR_SOIL)
        
        
    def MakeSmokeAt(self,x,y,index:int):
        self.Dot(x, y, self.cfg.COLOR_SMOKE )        
        
        
        
        
    def DrawDigit(self,id,xpos,ypos):
        if (xpos<0) or (ypos<0):
            return 0

        img = self.GetSprite("digit",id).convert('1')
        w, h = img.size
        pix = img.load()
        ypos -= h
        for x in range(w):
            for y in range(h):
                if (xpos+x>=self.w) or (xpos+x<0):
                    continue
                if (ypos+y>=self.h) or (ypos+y<0):
                    continue
                if (pix[x,y]==self.BLACK):
                    self.Dot(xpos+x,ypos+y,self.cfg.COLOR_FG)

        return w