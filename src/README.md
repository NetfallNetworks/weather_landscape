# Weather Landscape Cloudflare Worker

This directory contains the Cloudflare Python Worker implementation for generating and serving weather landscape images.

## Structure

```
src/
├── index.py          # Main worker entry point
├── requirements.txt  # Python package dependencies (Pillow)
└── README.md        # This file
```

## How It Works

The worker has two main functions:

### 1. Scheduled Generation (Cron)
- Runs every 15 minutes (configurable in `wrangler.toml`)
- Fetches current weather from OpenWeather API
- Generates weather landscape image using existing `weather_landscape.py` code
- Uploads image to Cloudflare R2 storage
- Updates metadata in KV store

### 2. HTTP Serving
- `GET /` or `GET /current.png` - Serves the current image from R2
- `GET /status` - Returns generation status and metadata
- `POST /generate` - Manually triggers image generation

## Key Components

### `index.py`

**Main Functions:**
- `scheduled(event, env, ctx)` - Handles cron triggers
- `fetch(request, env, ctx)` - Handles HTTP requests
- `generate_weather_image(env)` - Generates the image
- `upload_to_r2(env, image_bytes, metadata)` - Uploads to R2

**Environment Bindings:**
- `env.WEATHER_IMAGES` - R2 bucket for images
- `env.CONFIG` - KV namespace for configuration
- `env.OWM_API_KEY` - OpenWeather API key (secret)
- `env.DEFAULT_LAT` - Default latitude
- `env.DEFAULT_LON` - Default longitude

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
