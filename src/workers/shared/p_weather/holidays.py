import os
import json
from dataclasses import dataclass
from typing import List,Tuple
import datetime


@dataclass
class WLHEntry:

    DEFAULT_HOUR = 12
    DEFAULT_MIN = 0
    DEFAULT_DAY = 1
    DEFAULT_MON = 1


    date: str
    sprite: str
    index: int
    time: str
    text: str
    yoffset: int
    xoffset: int
    stayhours: int  



    def __str__(self):
        return "%02i.%02i %02i:%02i %s %s" % (self.day,self.month,self.hour,self.min,self.sprite,self.text)

    @property
    def hour(self):
        (h,m,s) = self.Split(self.time,":",(self.DEFAULT_HOUR,self.DEFAULT_MIN,0)) 
        return h

    @property
    def min(self):
        (h,m,s) = self.Split(self.time,":",(self.DEFAULT_HOUR,self.DEFAULT_MIN,0)) 
        return m
        
    @property
    def day(self):
        (d,m,y) = self.Split(self.date,".",(self.DEFAULT_DAY,self.DEFAULT_MON,2000)) 
        return d

    @property
    def month(self):
        (d,m,y) = self.Split(self.date,".",(self.DEFAULT_DAY,self.DEFAULT_MON,2000)) 
        return m
    
        
    def Split(self,text:str,sep:str,default:Tuple):
        assert len(default) == 3
        s = text.split(sep)
        r = ()
        for i in range(3):
            if (i>=len(s)):
                v = default[i]
            else:
                try:
                    v = int(s[i])
                except ValueError:        
                    v = default[i]
            r = r + (v,)
        return r
            
            
    def MakeTimeStart(self,t:datetime.datetime):
        try:
            st = datetime.datetime(t.year,self.month, self.day, self.hour, self.min, 0, 0)
        except:
            st = None
        return st
        
    def MakeTimeStop(self,t:datetime.datetime):
        st = self.MakeTimeStart(t)
        if st==None:
            return None
        try:
            dt = datetime.timedelta( hours = self.stayhours )
        except:
            return  None
        return st+dt
   
        



class WLHolidays(object):

    FILEPREFIX = "holiday"
    FILEEXT = ".json"
    
    
    data: List[WLHEntry]
    
    @staticmethod
    def from_json(json_str: str) -> "BirthdayData":
        obj = json.loads(json_str)
        entries = [Entry(**item) for item in obj.get("data", [])]
        return BirthdayData(title=obj["title"], data=entries)    
    

    def __init__(self,path:str=None):
        self.Load(path)
        
     
        
        
    def Reset(self):
        self.data = []
        
        
    def Load(self,path:str):
        self.Reset()
        if (path==None):
            path="."
 
        files = [fn for fn in os.listdir(path) if fn.startswith(self.FILEPREFIX) and fn.endswith(self.FILEEXT) ]
        for filename in files:
            filepath = os.path.join(path,filename)
            try:
                with open(filepath) as f:
                    obj = json.load(f)
                entries = [WLHEntry(**item) for item in obj.get("data", [])]
                self.data += entries
                title = obj.get("title", "Unknown")
                print("Loaded %i of '%s' from '%s'" % (len(entries),obj.get("title", "something"),filepath))   
                for e in self.data:
                    t = e.MakeTimeStart( datetime.datetime.now() ) 
                    if (t==None):
                        print("Date error in %s" % str(e))   
            except Exception as e:
                print("Holidays file '%s' load error: %s" % (filepath, str(e)))
                continue
          
        
            
            
            
            
            
    def GetAll(self, t0 : datetime.datetime, t1: datetime.datetime) -> List[WLHEntry]:   
        result = []
        
        for e in self.data:
            t = e.MakeTimeStart(t0) 
            tt = e.MakeTimeStop(t1) 
            if t==None or tt==None:
                continue
            if t0<t and t1<t:
                continue
            if t0>tt and t1>tt:
                continue
            result.append(e)
            
        return result
                
         

