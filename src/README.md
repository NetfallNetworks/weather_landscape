# Weather Landscape Cloudflare Worker

This directory contains the Cloudflare Python Worker implementation for generating and serving weather landscape images.

## Structure

```
src/
├── index.py              # Main worker entry point and routing
├── requirements.txt      # Python dependencies (Pillow, pyodide packages)
├── templates/            # HTML templates (string.Template format)
│   ├── landing.html      # Homepage (/)
│   ├── forecasts.html    # ZIP code list (/forecasts)
│   ├── guide.html        # Reading guide (/guide)
│   └── admin.html        # Admin dashboard (/admin)
├── assets/               # Static assets bundled with worker
│   ├── styles.css        # Shared stylesheet
│   ├── diagram.png       # Weather encoding diagram
│   └── favicon.png       # Site icon (RGB house sprite)
└── README.md             # This file
```

## How It Works

The worker provides three main functions:

### 1. Web Interface
Serves a complete web UI with templating:
- **Templating**: Uses Python's built-in `string.Template` (no external dependencies)
- **Shared CSS**: All pages reference `/assets/styles.css`
- **Responsive Design**: Mobile-first with hamburger menu navigation
- **Routes**:
  - `/` - Landing page with project explanation
  - `/forecasts` - Card-based list of ZIP codes and formats
  - `/guide` - Comprehensive reading guide
  - `/admin` - Management dashboard
  - `/assets/*` - Static assets (CSS, images)

### 2. Scheduled Generation (Cron)
- Runs every 15 minutes (configurable in `wrangler.toml`)
- Processes all active ZIP codes from KV (`active_zips`)
- For each ZIP:
  - Fetches weather from OpenWeather API
  - Generates images in all configured formats
  - Uploads to R2 at `{zip}/{format}.{ext}`
  - Updates metadata in KV
- Supports multi-format generation per ZIP

### 3. Image Serving & API
- `GET /{zip}` - Serves latest image (default format)
- `GET /{zip}?{format}` - Serves specific format
- `GET /admin/status` - Returns generation status and metadata
- `POST /admin/generate?zip={zip}` - Manually triggers generation
- `POST /admin/activate?zip={zip}` - Activates ZIP for auto-generation
- `POST /admin/deactivate?zip={zip}` - Deactivates ZIP
- `POST /admin/formats/add` - Adds format to ZIP
- `POST /admin/formats/remove` - Removes format from ZIP

## Key Components

### `index.py`

**Main Worker Class:**
```python
class WeatherLandscapeWorker:
    async def on_fetch(self, request, env, ctx):
        # Handles all HTTP requests and routing

    async def scheduled(self, event, env, ctx):
        # Handles cron-triggered generation
```

**Templating Functions:**
```python
def load_template(template_name):
    # Loads HTML template from src/templates/

def render_template(template_name, **context):
    # Renders template with $variable substitution
```

**Environment Bindings:**
- `env.WEATHER_IMAGES` - R2 bucket for images
- `env.CONFIG` - KV namespace for configuration
- `env.OWM_API_KEY` - OpenWeather API key (secret)
- `env.DEFAULT_ZIP` - Fallback ZIP code

### Templating System

**Why string.Template?**
- Built-in to Python (no external dependencies)
- Works in Cloudflare Workers' Pyodide environment
- Lightweight and fast
- Simple `$variable` syntax

**Template Variables:**
Templates use `$variable` syntax for substitution:
```html
<h1>Available Forecasts ($zip_count)</h1>
<div class="zip-grid">
    $zip_links
</div>
```

**Rendering:**
```python
html = render_template('forecasts.html',
    zip_links=cards_html,
    zip_count=len(all_zips)
)
```

**JavaScript in Templates:**
Dollar signs in JavaScript must be escaped as `$$`:
```javascript
// In template:
const regex = /^\d{5}$$/;  // Note: $$ instead of $
```

### Asset Bundling

**wrangler.toml Configuration:**
```toml
# HTML templates as Text
[[rules]]
type = "Text"
globs = ["src/templates/*.html"]

# CSS as Text
[[rules]]
type = "Text"
globs = ["**/*.css"]

# Images as Data (binary)
[[rules]]
type = "Data"
globs = ["**/*.png", "**/*.bmp"]
```

**Serving Assets:**
Assets are served with proper content-type and caching:
```python
# CSS
return Response.new(css_content, headers={
    "content-type": "text/css; charset=UTF-8",
    "cache-control": "public, max-age=86400"
})

# Images (binary conversion required)
from js import Uint8Array
js_array = Uint8Array.new(len(image_bytes))
for i, byte in enumerate(image_bytes):
    js_array[i] = byte
```

## Dependencies

The worker uses the existing weather landscape generation code from the parent directory:

```python
from weather_landscape import WeatherLandscape
from configs import WLConfig_RGB_White
from p_weather.openweathermap import OpenWeatherMap
from p_weather.draw_weather import DrawWeather
```

## Local Development

```bash
# Install Wrangler CLI
npm install -g wrangler

# Run worker locally
wrangler dev

# Test the worker
curl http://localhost:8787/
curl http://localhost:8787/status
```

## Deployment

See `../DEPLOYMENT.md` for complete deployment instructions.

Quick deploy:
```bash
wrangler deploy
```

## Beta Limitations

⚠️ **Python Workers are in beta (as of Jan 2025)**

- Packages like Pillow work in local dev but may not deploy to production
- Only Python standard library is guaranteed to work in production
- Worker bundle size may exceed limits with large packages

See `../DEPLOYMENT.md` for workarounds and alternatives.

## Configuration

### Secrets (set via wrangler)
```bash
wrangler secret put OWM_API_KEY
wrangler secret put DEFAULT_LAT  # optional
wrangler secret put DEFAULT_LON  # optional
```

### Environment Variables (in wrangler.toml)
```toml
[vars]
DEFAULT_LAT = 52.196136
DEFAULT_LON = 21.007963
IMAGE_WIDTH = 296
IMAGE_HEIGHT = 128
```

### KV Configuration
```bash
# Set image variant
wrangler kv:key put --namespace-id YOUR_ID "config:variant" "rgb_white"
```

## Monitoring

```bash
# Stream logs
wrangler tail

# Check R2 files
wrangler r2 object list weather-landscapes

# Check KV data
wrangler kv:key list --namespace-id YOUR_ID
```

## Troubleshooting

### Common Issues

1. **"Module not found" errors**
   - Ensure parent directory modules are accessible
   - Check Python path configuration

2. **"OWM_API_KEY not set"**
   - Set secret: `wrangler secret put OWM_API_KEY`

3. **Pillow import fails in production**
   - Expected beta limitation
   - Monitor [Python Workers changelog](https://developers.cloudflare.com/workers/languages/python/)

## Future Enhancements

Potential improvements once Python Workers exit beta:

- [ ] Support multiple image variants (configurable via KV)
- [ ] Support multiple locations (per-location endpoints)
- [ ] Archive historical images to R2
- [ ] Add webhook notifications on generation
- [ ] Implement image comparison (only upload if changed)
- [ ] Add custom event overlays (holidays, birthdays)

## References

- [Cloudflare Python Workers](https://developers.cloudflare.com/workers/languages/python/)
- [R2 Documentation](https://developers.cloudflare.com/r2/)
- [Workers KV](https://developers.cloudflare.com/kv/)
- [Parent Project README](../README.md)
