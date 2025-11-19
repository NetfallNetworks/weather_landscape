"""
Weather Landscape Workers

This package contains the four specialized workers:
- web.py: HTTP request handling
- weather_fetcher.py: Cron-triggered weather fetching
- job_dispatcher.py: Fan-out from weather-ready to generation jobs
- landscape_generator.py: Queue consumer for image generation
"""

from .web import WebWorker
from .weather_fetcher import WeatherFetcher
from .job_dispatcher import JobDispatcher
from .landscape_generator import LandscapeGenerator

__all__ = ['WebWorker', 'WeatherFetcher', 'JobDispatcher', 'LandscapeGenerator']
