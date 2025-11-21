"""
Weather landscape configuration classes for different output formats
"""

from .p_weather.configuration import WLBaseSettings
import os

# Detect if running in Cloudflare Workers
try:
    from js import fetch
    CLOUDFLARE_WORKER = True
    # In Workers, files are bundled at root level
    BASE_PATH = ""
except ImportError:
    CLOUDFLARE_WORKER = False
    # Local development uses workers/landscape/src/ prefix
    BASE_PATH = "workers/landscape/src/"


class WLConfig_BW(WLBaseSettings):
    TITLE = "BW"
    WORK_DIR = "tmp"
    OUT_FILENAME = "landscape_wb"
    OUT_FILEEXT = ".bmp"
    TEMPLATE_FILENAME = os.path.join(BASE_PATH, "p_weather/template_wb.bmp")
    SPRITES_DIR = os.path.join(BASE_PATH, "p_weather/sprite")
    POSTPROCESS_INVERT = False
    POSTPROCESS_EINKFLIP = False
    TEMPUNITS_MODE = WLBaseSettings.TEMP_UNITS_FAHRENHEIT


class WLConfig_EINK(WLConfig_BW):
    TITLE = "BW EINK"
    OUT_FILENAME = "landscape_eink"
    POSTPROCESS_INVERT = False
    POSTPROCESS_EINKFLIP = True


class WLConfig_BWI(WLConfig_BW):
    TITLE = "BW inverted"
    OUT_FILENAME = "landscape_wbi"
    POSTPROCESS_INVERT = True
    POSTPROCESS_EINKFLIP = False


class WLConfig_RGB_White(WLBaseSettings):
    TITLE = "Color, white BG"
    WORK_DIR = "tmp"
    OUT_FILENAME = "landscape_rgb_w"
    OUT_FILEEXT = ".png"
    SPRITES_DIR = os.path.join(BASE_PATH, "p_weather/sprite_rgb")
    TEMPLATE_FILENAME = os.path.join(BASE_PATH, "p_weather/template_rgb.bmp")

    POSTPROCESS_INVERT = False
    POSTPROCESS_EINKFLIP = False
    SPRITES_MODE = WLBaseSettings.SPRITES_MODE_RGB
    TEMPUNITS_MODE = WLBaseSettings.TEMP_UNITS_FAHRENHEIT

    COLOR_SOIL = (148, 82, 1)
    COLOR_SMOKE = (127, 127, 127)
    COLOR_BG = (255, 255, 255)
    COLOR_FG = (0, 0, 0)
    COLOR_RAIN = (10, 100, 148)
    COLOR_SNOW = (194, 194, 194)


class WLConfig_RGB_Black(WLConfig_RGB_White):
    TITLE = "Color, black BG"
    OUT_FILENAME = "landscape_rgb_b"

    COLOR_SOIL = (148, 82, 1)
    COLOR_SMOKE = (127, 127, 127)
    COLOR_BG = (0, 0, 0)
    COLOR_FG = (255, 255, 255)
    COLOR_RAIN = (122, 213, 255)
    COLOR_SNOW = (255, 255, 255)
