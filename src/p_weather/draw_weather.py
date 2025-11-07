
from p_weather.sprites import Sprites
from p_weather.sprites_rgb import SpritesRGB
from p_weather.openweathermap import OpenWeatherMap,WeatherInfo
from p_weather.sunrise import sun
from p_weather.configuration import WLBaseSettings


import datetime 
from PIL import Image
import random


class DrawWeather():


    
    
    @staticmethod
    def mybeizelfnc(t,d0,d1,d2,d3):
        return  (1-t)*( (1-t)*((1-t)*d0+t*d1 ) + t*( (1-t)*d1 + t*d2)) + t*( (1-t)*( (1-t)*d1 + t*d2)+t*((1-t)*d2 +t*d3))


    def mybezier(self,x,xa,ya,xb,yb):
        xc = (xb+xa)/2.0
        d = xb-xa
        t = float(x-xa)/float(d)
        y = DrawWeather.mybeizelfnc(t,ya,ya,yb,yb)
        return int(y)
        #print(t,x,y)


    @staticmethod
    def SpritesFactory(cfg:WLBaseSettings,canvasimag:Image):
        if cfg.SPRITES_MODE == WLBaseSettings.SPRITES_MODE_RGB:
            return SpritesRGB(cfg,canvasimag)
        elif cfg.SPRITES_MODE == WLBaseSettings.SPRITES_MODE_BW:
            return Sprites(cfg.SPRITES_DIR,canvasimag)
        else: 
            return None
            
            
    @staticmethod
    def ApplyPostprocess(sprite:Sprites,cfg:WLBaseSettings):
        if (cfg.POSTPROCESS_EINKFLIP):
            sprite.EINKFlip()
        if (cfg.POSTPROCESS_INVERT):
            sprite.BWInvert()
        return sprite.GetCanvas()            
            
            

    def __init__(self,img:Image,config:WLBaseSettings):
        self.cfg = config
        self.sprite = DrawWeather.SpritesFactory(self.cfg,img)
        assert self.sprite != None
        (self.IMGEWIDTH,self.IMGHEIGHT) = img.size


    def TimeDiffToPixels(self,dt):
       ds = dt.total_seconds() 
       secondsperpixel = (WeatherInfo.FORECAST_PERIOD_HOURS*60*60) / self.cfg.DRAW_XSTEP
       return int ( ds / secondsperpixel )


    def DegToPix(self,t):
        n = (t - self.tmin)/self.degreeperpixel
        y = self.ypos+self.cfg.DRAW_YSTEP - int(n)
        return y



    def BlockRange(self,tline,x0,x1):
        for x in range(x0,x1):
            tline[x] = Sprites.DISABLED
            


    def DrawTemperature(self,f:WeatherInfo,x:int,y:int):
        if (f.IsCelsius):
            self.sprite.DrawInt(f.PrintableTemperature,x,y+10,True,2)
        else:
            self.sprite.DrawInt(f.PrintableTemperature,x,y+10,False,1)


    
    def Draw(self,owm:OpenWeatherMap):
        self.DrawEx(self.cfg.DRAWOFFSET,owm)
        return DrawWeather.ApplyPostprocess(self.sprite,self.cfg)


  

    #todo: add thunderstorm
    #todo: add fog
    def DrawEx(self,ypos:int,owm:OpenWeatherMap):

        xstart = self.cfg.DRAW_XSTART
        xstep = self.cfg.DRAW_XSTEP
        ystep = self.cfg.DRAW_YSTEP
        xflat = self.cfg.DRAW_XFLAT

        self.picheight = self.IMGHEIGHT
        self.picwidth = self.IMGEWIDTH
        self.ypos = ypos

        nforecasrt = ( (self.picwidth-xstart)/xstep ) 
        maxtime = datetime.datetime.now() + datetime.timedelta(hours=WeatherInfo.FORECAST_PERIOD_HOURS*nforecasrt)

        (self.tmin,self.tmax) = owm.GetTempRange(maxtime)
        self.temprange = self.tmax-self.tmin
        if ( self.temprange < ystep ):
            self.degreeperpixel = self.cfg.DRAW_DEFAULT_DEGREE_PER_PIXEL
        else:
            self.degreeperpixel = self.temprange/float(ystep)
        
        #print("tmin = %f , tmax = %f, range=%f" % (self.tmin,self.tmax,self.temprange))

        xpos=0
        tline = [0]*(self.picwidth+xstep*2)
        f = owm.GetCurr()
        oldtemp = f.temp
        oldy = self.DegToPix(oldtemp)
        for i in range(xstart):
            tline[i] = oldy
        yclouds = int(ypos-ystep/2)
        print( str(f) )

        self.sprite.Draw("house",0,xpos,oldy) 
        
       
        # convert pressure to smoke angle 
        curr_hpa = owm.GetCurr().pressure
        smokeangle_deg = ((curr_hpa - owm.cfg.PRESSURE_MIN) / (owm.cfg.PRESSURE_MAX-owm.cfg.PRESSURE_MIN) )*85 + 5
        if (smokeangle_deg<0):
            smokeangle_deg=0
        if (smokeangle_deg>90):
            smokeangle_deg=90
        self.sprite.DrawSmoke(xpos+21,self.picheight-oldy+23,smokeangle_deg)
        
        self.DrawTemperature(f,xpos+8,oldy)
        self.sprite.DrawCloud(f.clouds,xpos,yclouds,self.cfg.DRAW_XSTART,ystep/2)
        self.sprite.DrawRain(f.rain,xpos,yclouds,xstart,tline)
        self.sprite.DrawSnow(f.snow,xpos,yclouds,xstart,tline)


        t = datetime.datetime.now()#+datetime.timedelta(hours = 1, minutes=0)
        
        
        dt = datetime.timedelta(hours=WeatherInfo.FORECAST_PERIOD_HOURS)
        tf = t 
        
        x0 = int(xstart)
        xpos = x0
        nforecasrt = int(nforecasrt)

        n = int( (xstep-xflat)/2 )
        for i in range(nforecasrt+1):
            f = owm.Get(tf)
            if (f==None):
                continue
                
            #f.Print()
            
            newtemp = f.temp
            newy = self.DegToPix(newtemp)
            
            for i in range(n):
                tline[xpos+i] = self.mybezier(xpos+i,xpos,oldy,xpos+n,newy)

            for i in range(xflat):
                tline[int(xpos+i+n)] = newy

            xpos+=n+xflat

            n = (xstep-xflat)
            oldtemp = newtemp
            oldy = newy
            tf += dt

        
        tline0 = tline.copy()
        
        self.BlockRange(tline,0,x0)
        
        s=sun(owm.LAT,owm.LON) 
        tf = t 
        xpos = xstart
        objcounter=0
        for i in range(nforecasrt+1):
            f = owm.Get(tf)
            if (f==None):
                continue

            t_sunrise = s.sunrise(tf)
            t_sunset = s.sunset(tf) 
            t_noon = datetime.datetime(tf.year,tf.month,tf.day,12,0,0,0)
            t_midn = datetime.datetime(tf.year,tf.month,tf.day,0,0,0,0)+datetime.timedelta(days=1)
            
            #print("---",tf," - ",tf + dt,"   ",t_noon,t_midn)

            ymoon = ypos-ystep*5/8

            if (tf<=t_sunrise) and (tf+dt>t_sunrise):
                dx = self.TimeDiffToPixels(t_sunrise-tf)  - xstep/2
                self.sprite.Draw("sun",0,xpos+dx,ymoon)
                objcounter+=1
                if (objcounter==2):
                    break;

            if (tf<=t_sunset) and (tf+dt>t_sunset):
                dx = self.TimeDiffToPixels(t_sunset-tf)  - xstep/2
                self.sprite.Draw("moon",0,xpos+dx,ymoon)
                objcounter+=1
                if (objcounter==2):
                    break;

            if (tf<=t_noon) and (tf+dt>t_noon):
                dx = self.TimeDiffToPixels(t_noon-tf)  - xstep/2
                ix =int(xpos+dx)
                self.sprite.Draw("flower",1,ix,tline[ix]+1)
                self.BlockRange(tline,ix-self.cfg.DRAW_FLOWER_LEFT_PX,ix+self.cfg.DRAW_FLOWER_RIGHT_PX)


            if (tf<=t_midn) and (tf+dt>t_midn):
                dx = self.TimeDiffToPixels(t_midn-tf)  - xstep/2
                ix =int(xpos+dx)
                self.sprite.Draw("flower",0,ix,tline[ix]+1)      
                self.BlockRange(tline,ix-self.cfg.DRAW_FLOWER_LEFT_PX,ix+self.cfg.DRAW_FLOWER_RIGHT_PX)
                    

            xpos+=xstep
            tf += dt
        

        xleft = 0
        tf = t+dt*(nforecasrt+1)
        for holiday_obj in self.cfg.GetAllHolidays(t,tf ):
            assert holiday_obj!=None
            t_holiday = holiday_obj.MakeTimeStart(t) 
            assert t_holiday!= None
            dx = self.TimeDiffToPixels(t_holiday-t) 
            hypos = holiday_obj.yoffset
            hxpos = xleft+dx+holiday_obj.xoffset 
            #print(">>>",xleft,dx,t_holiday,holiday_obj)
            if (hxpos<0):#todo: do a smooth move to the left instead of disappearing
                hxpos=0
            self.sprite.Draw(holiday_obj.sprite,holiday_obj.index,hxpos,hypos)


 
        istminprinted = False
        istmaxprinted = False
        tf = t 
        xpos = xstart
        n = int( (xstep-xflat)/2 )
        f_used = []
        
        for i in range(nforecasrt+1):
            f = owm.Get(tf)
            if (f==None):
                continue
 
            print( str(f) )
            dx = self.TimeDiffToPixels(f.t-tf)  - xstep/2
            ix =int(xpos+dx)
            
            yclouds = int( ypos-ystep/2 )
            
            if (f.temp==self.tmin) and (not istminprinted):
                self.DrawTemperature(f,xpos+n,tline0[xpos+n])
                istminprinted = True
            
            if (f.temp==self.tmax) and (not istmaxprinted):
                self.DrawTemperature(f,xpos+n,tline0[xpos+n])
                istmaxprinted = True


            # todo: apply sprite line width 
            if not (f in f_used):
                self.sprite.DrawWind(f.windspeed,f.winddeg,ix,tline)
                self.sprite.DrawCloud(f.clouds,ix,yclouds,xstep,ystep/2)
                self.sprite.DrawRain(f.rain,ix,yclouds,xstep,tline0)
                self.sprite.DrawSnow(f.snow,ix,yclouds,xstep,tline0)
                f_used.append(f)
                
            

            xpos+=xstep
            tf += dt




        BLACK = 0
        
        self.sprite.DrawSoil(tline0)





