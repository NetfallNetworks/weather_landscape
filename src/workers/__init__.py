"""
Weather Landscape Workers

This package contains the five specialized workers:
- web.py: HTTP request handling
- zip_scheduler.py: Cron-triggered, enqueues ZIPs for processing
- weather_fetcher.py: Queue consumer, fetches weather for ONE ZIP
- job_dispatcher.py: Fan-out from weather-ready to generation jobs
- landscape_generator.py: Queue consumer for image generation
"""

from .web import WebWorker
from .zip_scheduler import ZipScheduler
from .weather_fetcher import WeatherFetcher
from .job_dispatcher import JobDispatcher
from .landscape_generator import LandscapeGenerator

__all__ = ['WebWorker', 'ZipScheduler', 'WeatherFetcher', 'JobDispatcher', 'LandscapeGenerator']
