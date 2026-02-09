# Deployment Guide: Weather Landscape Cloudflare Worker

This guide walks through deploying the Weather Landscape project as a Cloudflare Python Worker with R2 storage and KV configuration.

## 📋 Prerequisites

1. **Cloudflare Account** with Workers enabled (free tier works!)
2. **Wrangler CLI** installed and authenticated
3. **OpenWeather API Key** (free tier at https://openweathermap.org/api)
4. **Node.js >= 20** and **npm** (for Wrangler)
5. **uv** (Python package manager) - https://docs.astral.sh/uv/

## 🚀 Quick Start

### Step 1: Install Wrangler

```bash
npm install -g wrangler

# Login to Cloudflare
wrangler login
```

### Step 2: Create R2 Bucket

```bash
# Create the R2 bucket for storing images
wrangler r2 bucket create weather-landscapes
```

### Step 3: Create KV Namespace

```bash
# Create KV namespace for configuration
wrangler kv namespace create CONFIG

# This will output a namespace ID like:
# { binding = "CONFIG", id = "abc123..." }
# Copy the ID and update wrangler.toml:
# Replace YOUR_KV_NAMESPACE_ID with your actual ID
```

### Step 4: Set Up Local Config

```bash
# Copy the example env file and fill in your KV namespace ID from Step 3
cp .wrangler.local.env.example .wrangler.local.env

# Generate local wrangler config files for each worker
./setup-local-config.sh
```

### Step 5: Deploy Workers

Each worker is deployed individually from its directory:

```bash
# Deploy all workers at once
./deploy-all.sh

# Or deploy a single worker (e.g., landscape generator)
cd workers/landscape && uv run pywrangler deploy -c wrangler.local.toml
```

### Step 6: Set Secrets

**IMPORTANT:** Secrets must be set AFTER the worker is deployed:

```bash
# Set your OpenWeather API key for the fetcher worker
wrangler secret put OWM_API_KEY -c workers/fetcher/wrangler.toml
# When prompted, paste your API key
```

## 🔧 Configuration

### Environment Variables (wrangler.toml)

Edit `wrangler.toml` to customize:

```toml
[vars]
DEFAULT_LAT = 52.196136      # Your default latitude
DEFAULT_LON = 21.007963      # Your default longitude
IMAGE_WIDTH = 296            # Image width in pixels
IMAGE_HEIGHT = 128           # Image height in pixels
UPDATE_INTERVAL_MINUTES = 15 # How often to regenerate
```

### Secrets (via wrangler secret)

**Required:**
- `OWM_API_KEY` - Your OpenWeather API key

**Optional:**
- `DEFAULT_LAT` - Override default latitude
- `DEFAULT_LON` - Override default longitude

### KV Configuration

The worker stores configuration in KV. To set image variant preference:

```bash
# Use wrangler to set KV values (replace with your namespace ID)
wrangler kv key put --namespace-id YOUR_KV_NAMESPACE_ID "config:variant" "rgb_white"
```

Available variants:
- `rgb_white` - Color image with white background (default)
- `rgb_black` - Color image with black background
- `bw` - Black and white
- `bw_inverted` - Inverted black and white
- `eink` - E-Ink optimized

## 🌐 Web Interface & Routes

Once deployed, your worker provides a complete web interface:

### Public Web Pages

**`GET /`** - Landing Page
Beautiful homepage with:
- Project explanation and "Big Picture" diagram
- Quick decoder ring for understanding landscapes
- Live example weather landscape
- Links to forecasts and reading guide

**`GET /forecasts`** - Forecasts Page
Card-based interface showing:
- All configured ZIP codes
- Status badges (active/inactive)
- Available formats as clickable buttons
- Responsive grid layout

**`GET /guide`** - Reading Guide
Comprehensive guide including:
- Live weather landscape example
- Annotated diagram explaining all elements
- Feature cards for each weather element
- Complete reference table

**`GET /{zip}`** - Weather Image (Default Format)
```bash
# Returns latest RGB Light image for ZIP 78729
curl https://weather-landscape-worker.YOUR-SUBDOMAIN.workers.dev/78729 > weather.png
```

**`GET /{zip}?{format}`** - Weather Image (Specific Format)
```bash
# Get dark theme version
curl https://weather-landscape-worker.YOUR-SUBDOMAIN.workers.dev/78729?rgb_dark > weather_dark.png

# Get E-Ink version
curl https://weather-landscape-worker.YOUR-SUBDOMAIN.workers.dev/78729?eink > weather_eink.bmp
```

### Admin Dashboard

**`GET /admin`** - Admin Dashboard
Web-based management interface for:
- Viewing all ZIP codes (from R2 and KV)
- Toggling active/inactive status per ZIP
- Managing formats per ZIP (checkboxes)
- Manually triggering generation
- Adding new ZIP codes

### API Endpoints

**`GET /admin/status`** - Status & Metadata
```bash
curl https://weather-landscape-worker.YOUR-SUBDOMAIN.workers.dev/admin/status
```

Returns:
```json
{
  "status": {
    "lastRun": "2025-01-10T12:00:00Z",
    "totalZips": 3,
    "successCount": 3,
    "errorCount": 0
  },
  "activeZips": ["78729", "90210"],
  "zipMetadata": {
    "78729": {
      "generatedAt": "2025-01-10T12:00:00Z",
      "latitude": 30.4515,
      "longitude": -97.7676,
      "zipCode": "78729"
    }
  }
}
```

**`POST /admin/generate?zip={zip}`** - Manual Generation
```bash
curl -X POST "https://weather-landscape-worker.YOUR-SUBDOMAIN.workers.dev/admin/generate?zip=78729"
```

**`POST /admin/activate?zip={zip}`** - Activate ZIP
```bash
curl -X POST "https://weather-landscape-worker.YOUR-SUBDOMAIN.workers.dev/admin/activate?zip=78729"
```

**`POST /admin/deactivate?zip={zip}`** - Deactivate ZIP
```bash
curl -X POST "https://weather-landscape-worker.YOUR-SUBDOMAIN.workers.dev/admin/deactivate?zip=78729"
```

**`POST /admin/formats/add?zip={zip}&format={format}`** - Add Format
```bash
curl -X POST "https://weather-landscape-worker.YOUR-SUBDOMAIN.workers.dev/admin/formats/add?zip=78729&format=rgb_dark"
```

**`POST /admin/formats/remove?zip={zip}&format={format}`** - Remove Format
```bash
curl -X POST "https://weather-landscape-worker.YOUR-SUBDOMAIN.workers.dev/admin/formats/remove?zip=78729&format=bw"
```

**`GET /admin/formats?zip={zip}`** - Get Formats for ZIP
```bash
curl "https://weather-landscape-worker.YOUR-SUBDOMAIN.workers.dev/admin/formats?zip=78729"
```

## 🕐 Scheduled Generation

The worker automatically generates new images every 15 minutes via cron trigger.

To change the schedule, edit `wrangler.toml`:

```toml
[triggers]
crons = ["*/15 * * * *"]  # Every 15 minutes
# crons = ["0 * * * *"]   # Every hour
# crons = ["0 */6 * * *"] # Every 6 hours
```

Cron syntax: `minute hour day month weekday`

## 🧪 Local Development

### Test Locally with Wrangler Dev

```bash
# Run the worker locally
wrangler dev

# This starts a local server at http://localhost:8787
# Note: Packages like Pillow work in local dev but may not deploy to production (beta limitation)
```

### Test Scheduled Events

```bash
# Trigger a scheduled event locally
curl "http://localhost:8787/__scheduled?cron=*+*+*+*+*"
```

## ⚠️ Known Limitations (Beta)

### Python Workers are in Beta

As of January 2025, Cloudflare Python Workers have these limitations:

1. **Package Deployment**: Packages like Pillow may not deploy to production
   - Works in local development (`wrangler dev`)
   - May fail or be stripped during production deployment

2. **Bundle Size**: WASM packages can exceed worker size limits

3. **Standard Library Only**: Production deployments currently only support Python standard library

### What This Means

- ✅ You can develop and test locally with full Pillow support
- ❌ Deployment to production may fail or image generation may not work
- 🔄 Monitor the [Cloudflare Workers Python changelog](https://developers.cloudflare.com/workers/languages/python/) for updates

### Workaround: Hybrid Approach

If package deployment doesn't work, you can use a hybrid approach:

1. **Python Script** (local or CI/CD): Generates images, uploads to R2
2. **JS Worker**: Serves images from R2 (simple, no package dependencies)

See `CLOUDFLARE-STORAGE-GUIDE.md` for the hybrid approach implementation.

## 🐛 Troubleshooting

### Issue: "Namespace not found"

**Solution:** Make sure you updated `wrangler.toml` with your actual KV namespace ID from Step 3.

### Issue: "OWM_API_KEY not set"

**Solution:** Set the secret using `wrangler secret put OWM_API_KEY`

### Issue: "Image generation failed" in production

**Possible Causes:**
1. Pillow package not available (beta limitation)
2. File system access issues
3. API rate limits

**Solutions:**
- Check worker logs: `wrangler tail`
- Verify package deployment: Look for Pillow in deployed bundle
- Consider hybrid approach if package deployment fails

### Issue: "Module not found" errors

**Solution:** Make sure you are deploying from the correct worker directory. Each worker has its own `src/` directory:
```
weather_landscape/
├── workers/
│   ├── landscape/           # Landscape generator worker
│   │   ├── src/
│   │   │   ├── landscape_generator.py  # Worker entry point
│   │   │   ├── weather_landscape.py    # Main class
│   │   │   ├── configs.py             # Configuration classes
│   │   │   └── p_weather/             # Weather module
│   │   ├── wrangler.toml
│   │   └── pyproject.toml
│   ├── web/                 # Web serving worker
│   ├── fetcher/             # Weather data fetcher
│   ├── scheduler/           # Job scheduler
│   └── dispatcher/          # Job dispatcher
├── deploy-all.sh
├── setup-local-config.sh
└── test_local_generation.py
```

## 📊 Monitoring

### View Worker Logs

```bash
# Stream live logs
wrangler tail

# View logs in Cloudflare Dashboard
# Workers & Pages > weather-landscape-worker > Logs
```

### Check Cron Execution

In the Cloudflare Dashboard:
1. Go to Workers & Pages > weather-landscape-worker
2. Click "Triggers" tab
3. View "Cron Triggers" section for execution history

### Monitor R2 Storage

```bash
# List files in R2 bucket
wrangler r2 object list weather-landscapes

# Get file info
wrangler r2 object get weather-landscapes/current.png
```

### Check KV Data

```bash
# List KV keys (replace with your namespace ID)
wrangler kv key list --namespace-id YOUR_KV_NAMESPACE_ID

# Get a value (replace with your namespace ID)
wrangler kv key get --namespace-id YOUR_KV_NAMESPACE_ID "status"
```

## 💰 Costs

### Free Tier Limits

**Workers:**
- ✅ 100,000 requests/day
- ✅ 10ms CPU time per invocation

**R2:**
- ✅ 10 GB storage
- ✅ 1M writes/month
- ✅ 10M reads/month
- ✅ No egress fees

**KV:**
- ✅ 100,000 reads/day
- ✅ 1,000 writes/day
- ✅ 1 GB storage

### Expected Usage (15min intervals)

- **Cron runs:** 96/day (4/hour × 24 hours)
- **R2 writes:** ~3,000/month (96/day × 30 days)
- **Storage:** ~100 MB (for current + some history)
- **CPU:** < 1 second per generation

**Result:** Well within free tier! 💚

## 🔐 Security Best Practices

1. **Never commit secrets** to version control
2. **Use wrangler secrets** for API keys (encrypted at rest)
3. **Rotate API keys** every 90 days
4. **Use custom domains** with authentication if needed
5. **Monitor logs** for suspicious activity

## 🚢 Continuous Deployment (Optional)

### GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy Worker

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Deploy to Cloudflare Workers
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
```

Set `CLOUDFLARE_API_TOKEN` in GitHub repo secrets.

## 📚 Additional Resources

- [Cloudflare Python Workers Docs](https://developers.cloudflare.com/workers/languages/python/)
- [R2 Documentation](https://developers.cloudflare.com/r2/)
- [Workers KV Documentation](https://developers.cloudflare.com/kv/)
- [Wrangler CLI Reference](https://developers.cloudflare.com/workers/wrangler/)
- [OpenWeather API Docs](https://openweathermap.org/api)

## 🆘 Getting Help

If you encounter issues:

1. Check worker logs: `wrangler tail`
2. Review Cloudflare Dashboard for errors
3. Consult `CLOUDFLARE-STORAGE-GUIDE.md` for R2/KV specifics
4. Check [Cloudflare Community Forums](https://community.cloudflare.com/c/developers/workers/)
5. File issues in the project repository

---

**Happy deploying! 🎨☁️**
