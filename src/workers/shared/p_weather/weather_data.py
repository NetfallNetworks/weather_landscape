"""
Weather data parser - parses raw API responses into WeatherInfo objects
No API dependencies - just takes JSON and creates structured data
"""

from .openweathermap import WeatherInfo
from .configuration import WLBaseSettings


class ParsedWeatherData:
    """
    Lightweight weather data container
    Parses raw OpenWeatherMap JSON into WeatherInfo objects
    No API key needed - just parsing
    """

    def __init__(self, cfg: WLBaseSettings, current_data: dict, forecast_data: dict):
        """
        Parse weather data from raw API responses

        Args:
            cfg: Configuration (for temperature units, etc)
            current_data: Raw current weather JSON from OWM API
            forecast_data: Raw forecast JSON from OWM API
        """
        self.cfg = cfg
        self.f = []

        # Store location coordinates from config
        self.LAT = cfg.OWM_LAT
        self.LON = cfg.OWM_LON

        # Capture timezone offset from API (in seconds from UTC)
        self.timezone_offset = current_data.get('timezone', 0)
        print(f"🌍 Location timezone offset: {self.timezone_offset}s ({self.timezone_offset/3600}h from UTC)")

        # Parse current weather
        current = WeatherInfo(current_data, self.cfg)
        self.f.append(current)

        # Parse forecast data
        if 'list' in forecast_data:
            for fdata in forecast_data['list']:
                if WeatherInfo.Check(fdata):
                    f = WeatherInfo(fdata, self.cfg)
                    self.f.append(f)

    def GetCurr(self):
        """Get current weather info"""
        if len(self.f) == 0:
            return None
        return self.f[0]

    def Get(self, time):
        """Get weather info at specific time"""
        for f in self.f:
            if f.t > time:
                return f
        return None

    def GetTempRange(self, maxtime):
        """Get temperature range up to maxtime"""
        if len(self.f) == 0:
            return None
        tmax = -999
        tmin = 999
        isfirst = True
        for f in self.f:
            if isfirst:
                isfirst = False
                continue
            if f.t > maxtime:
                break
            if f.temp > tmax:
                tmax = f.temp
            if f.temp < tmin:
                tmin = f.temp
        return (tmin, tmax)
