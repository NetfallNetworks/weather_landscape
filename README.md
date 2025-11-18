# Weather as Landscape
Visualizing Weather Forecasts Through Landscape Imagery

![house](pic/house.png)

Traditional weather stations often display sensor readings as raw numerical data. Navigating these dashboards can be overwhelming and stressful, as it requires significant effort to locate, interpret, and visualize specific parameters effectively.

Viewing a landscape image feels natural to the human eye. The calming effect of observing landscape elements reduces stress and requires minimal effort, allowing for a more relaxed visual experience.

The method below demonstrates how to encode weather information within a landscape image, with no or minimal reliance on numerical data.



## Encoding principles

The landscape depicts a small house in the woods. The horizontal axis of the image represents a 24-hour timeline, starting from the current moment on the left, marked by the house, and extending to the conditions of the next day on the right. Various landscape elements distributed along the vertical axis symbolize weather events and conditions. The further an event is from the present, the farther it is positioned to the right in the image.


![encode](pic/encode.png)


The following information can be encoded within the landscape image:

- Time markers to simplify timeline navigation:
  - Sunrise and sunset times
  - Noon and midnight
- Weather forecast information:
  - Wind direction and strength
  - Temperature fluctuations
  - Maximum and minimum temperature values
  - Cloud cover
  - Precipitation
- Current weather conditions:
  - Temperature
  - Atmospheric pressure
- Non weather events:
  - Birthdays
  - Holidays
  


## Implementation

The image generation code is written in [Python](https://www.python.org/) using the [Pillow](https://python-pillow.org/) library and is based on data from [OpenWeather](https://openweathermap.org/). The image is designed specifically for use on a 296x128 E-Ink display. The code tested on Python 3.9.


| Event image | Description |
|----------|------------|
|![example](pic/sun_00.png)| Sunrise | 
|![example](pic/moon_00.png)| Sunset |
|![example](pic/cloud_30.png)| Cloud cover |
|![example](pic/house_00.png)| Current time position|
|![example](pic/flower_00.png)| Midnight |
|![example](pic/flower_01.png)| Midday |
|![example](pic/sprites_south.png)| South wind |
|![example](pic/sprites_east.png)| East wind |
|![example](pic/sprites_west.png)| West wind |
|![example](pic/sprites_north.png)| North wind |
|![example](pic/rain.png)| Rain|
|![example](pic/snow.png)| Snow|
|![example](pic/pres_high.png)| High atmospheric pressure |
|![example](pic/pres_norm.png)| Normal atmospheric pressure |
|![example](pic/pres_low.png)| Low atmospheric pressure |
|![example](pic/holiday.png)| [Non-weather event](holiday.md): someone's birthday. |

The taller the trees, the stronger the wind is expected to be. A mix of different tree types in the forest indicates an intermediate wind direction.



## Examples

|&nbsp;Landscape&nbsp;image&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;| Description |
|----------|------------|
|![example](pic/weather_test.bmp)| It’s around noon, with clear skies and a few clouds expected. A moderate north wind will develop overnight. Temperatures are currently rising but will begin to fall after sunset, reaching their lowest point before sunrise. During this time, the wind is expected to shift to the northeast.|
|![example](pic/test_20240903_043826.bmp)| The sun is rising and it will be a hot sunny day with a light southeast breeze. The temperature will remain high even after sunset, and the wind will shift to the east, becoming stronger throughout the evening.|
|![example](pic/test_09B0B1083315.bmp)| It will be cold and rainy throughout the day and night. The south wind will shift to the northwest overnight. Don’t forget that someone’s birthday is tomorrow. |


## How the landscape changed during the day

![Dynamic](pic/dynamic.gif)



## Running the code


#### Preparing environment Linux
```
./makevenv.sh
```
```
source .venv/bin/activate
```

#### Preparing environment Windows
```
makevenv.bat
```
```
.venv/Scripts/Activate
```

#### Image creation test

Update **OWM_KEY** variable in the `secrets.py` with your OpenWeather API key.

(optional) Change the coordinates in `secrets.py` to your location.

```
python run_test.py
```

Find generated images in the "tmp" folder.

#### Run server

```
python run_server.py
```

![Setup](pic/server_start_screenshot.png)

Access the server page from a browser to see the number of generated images.


## Cloudflare Deployment ☁️

Deploy your weather landscape as a globally distributed Cloudflare Worker with automatic image generation, edge caching, and a beautiful web interface!

**Features:**
- 🕐 Automatic image generation every 15 minutes (configurable)
- 🌍 Global edge distribution via Cloudflare's network
- 💾 Image storage in R2 (S3-compatible object storage)
- 🔑 Secure configuration via KV store and Secrets
- 📍 **Multi-ZIP support** - Generate images for multiple locations
- 🎨 **Multi-format support** - Generate multiple image formats per ZIP
- 🌐 **Web UI** - Beautiful interface for browsing forecasts and reading guides
- ⚙️ **Admin dashboard** - Manage ZIP codes and formats via web interface
- 💰 Free tier friendly (well within limits)

### Quick Deploy

```bash
# Install Wrangler CLI
npm install -g wrangler

# Login to Cloudflare
wrangler login

# Create R2 bucket and KV namespace
wrangler r2 bucket create weather-landscapes
wrangler kv namespace create CONFIG

# Update wrangler.toml with your KV namespace ID

# Deploy!
wrangler deploy

# Set secrets AFTER deployment
wrangler secret put OWM_API_KEY
```

### Web Interface

Your weather landscape will be accessible via a clean, responsive web UI:

**Public Routes:**
- `/` - Landing page with project explanation and quick decoder
- `/forecasts` - Card-based list of all available ZIP codes and formats
- `/guide` - Comprehensive reading guide with live examples
- `/{zip}` - Latest weather landscape image for specific ZIP (default format)
- `/{zip}?{format}` - Specific format (e.g., `/78729?rgb_dark`)

**Admin Routes:**
- `/admin` - Dashboard for managing ZIP codes, formats, and triggering generation

**Assets:**
- `/assets/styles.css` - Shared stylesheet
- `/assets/diagram.png` - Weather encoding diagram
- `/favicon.png` - Site icon

**📚 Full deployment guide:** See [DEPLOYMENT.md](DEPLOYMENT.md)

**📍 Multi-ZIP guide:** See [MULTI-ZIP-GUIDE.md](MULTI-ZIP-GUIDE.md) for managing multiple locations

### Multi-Format Generation 🎨

Generate images in multiple formats per ZIP code! Each ZIP can have its own format configuration stored in KV. By default, only the `rgb_light` format is generated.

**Available Formats:**
- `rgb_light` (default, always generated) - Color image with light theme (.png)
- `rgb_dark` - Color image with dark theme (.png)
- `bw` - Black & White for E-Ink displays (.bmp)
- `eink` - Black & White with 90° rotation for E-Ink (.bmp)
- `bwi` - Black & White inverted (.bmp)

**Managing Formats:**

**Via Admin Dashboard (Recommended):**
1. Navigate to `/admin` in your deployed worker
2. Each ZIP code shows checkboxes for available formats
3. Check/uncheck formats to enable/disable them
4. Click "Generate Now" to immediately create images for all enabled formats

**Via API:**

```bash
# Add RGB Dark format to ZIP 78729
curl -X POST "https://your-worker.workers.dev/admin/formats/add?zip=78729&format=rgb_dark"

# Add Black & White format
curl -X POST "https://your-worker.workers.dev/admin/formats/add?zip=78729&format=bw"

# Remove a format (cannot remove default rgb_light)
curl -X POST "https://your-worker.workers.dev/admin/formats/remove?zip=78729&format=bw"

# Get current formats for a ZIP
curl "https://your-worker.workers.dev/admin/formats?zip=78729"
# Returns: {"zip": "78729", "formats": ["rgb_light", "rgb_dark"], "available": [...]}

# Generate all configured formats for a ZIP
curl -X POST "https://your-worker.workers.dev/admin/generate?zip=78729"
```

**Accessing Different Formats:**

Request specific formats using query parameters:

```
# Default format (rgb_light)
https://your-worker.workers.dev/78729

# Request via query parameter
https://your-worker.workers.dev/78729?bw
https://your-worker.workers.dev/78729?eink
https://your-worker.workers.dev/78729?rgb_dark

# Format names can use hyphens or underscores
https://your-worker.workers.dev/78729?rgb_dark
https://your-worker.workers.dev/78729?rgb-dark  # same result
```

**Format Request Behavior:**
- If the requested format doesn't exist, the default format is returned
- If an invalid format is requested, the default format is returned
- Format names can use hyphens or underscores (e.g., `rgb_light` or `rgb-dark`)
- Each ZIP has its own format configuration stored in KV (`formats:{zip}`)

**Storage:**

One file per format is stored in R2:
- `{zip}/rgb_light.png` (default format)
- `{zip}/bw.bmp`
- `{zip}/eink.bmp`
- `{zip}/rgb_dark.png`
- `{zip}/bwi.bmp`

The routing layer serves the appropriate format based on the request.


## E-Ink module

<!-- ![2.9inch e-Paper Module](pic/eink.jpg) -->
![Setup](pic/hardware.jpg)

The hardware setup includes an [ESP32 development board](https://www.adafruit.com/product/3269) and [2.9inch E-Ink display module](https://www.waveshare.com/2.9inch-e-paper-module.htm). Currently, the setup only displays an image sourced from the internet, updating every 15 minutes. It is uncertain whether the image generation code can be adapted for use with MicroPython on the ESP32 at this time.

[More information](esp32/README.md)


## Phone

![Setup](pic/landscape_rgb_w.png)

During the test, several images are generated. The black-and-white images are intended for use with an E-Ink module, while the color images can be placed on a phone's home screen. For Android devices, there is an app called [Web Image Widget](https://play.google.com/store/apps/details?id=com.ibuffed.webimagewidget&hl=en) that allows you to create a widget displaying an image from the internet. To use it, start the server script from the repository and add a widget that points to one of the generated images.

![Android](pic/color_phone_screenshot.jpg)


