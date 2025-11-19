"""
Weather Landscape Workers

This package contains the three specialized workers:
- web.py: HTTP request handling
- weather_fetcher.py: Cron-triggered weather fetching and job enqueueing
- landscape_generator.py: Queue consumer for image generation
"""

from .web import WebWorker
from .weather_fetcher import WeatherFetcher
from .landscape_generator import LandscapeGenerator

__all__ = ['WebWorker', 'WeatherFetcher', 'LandscapeGenerator']
