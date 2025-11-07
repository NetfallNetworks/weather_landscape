# Deployment Guide: Weather Landscape Cloudflare Worker

This guide walks through deploying the Weather Landscape project as a Cloudflare Python Worker with R2 storage and KV configuration.

## 📋 Prerequisites

1. **Cloudflare Account** with Workers enabled (free tier works!)
2. **Wrangler CLI** installed and authenticated
3. **OpenWeather API Key** (free tier at https://openweathermap.org/api)
4. **Node.js/npm** (for Wrangler)

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

### Step 4: Deploy the Worker

```bash
# Deploy to Cloudflare
wrangler deploy

# You'll see output like:
# Published weather-landscape-worker (X.XX sec)
#   https://weather-landscape-worker.YOUR-SUBDOMAIN.workers.dev
```

### Step 5: Set Secrets

**IMPORTANT:** Secrets must be set AFTER the worker is deployed:

```bash
# Set your OpenWeather API key as a secret
wrangler secret put OWM_API_KEY --name weather-landscape-worker
# When prompted, paste your API key

# Optionally, set custom coordinates (or use defaults in wrangler.toml)
wrangler secret put DEFAULT_LAT --name weather-landscape-worker
# Enter your latitude (e.g., 30.2672)

wrangler secret put DEFAULT_LON --name weather-landscape-worker
# Enter your longitude (e.g., -97.7431)
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

## 📡 API Endpoints

Once deployed, your worker exposes these endpoints:

### `GET /` or `GET /current.png`
Returns the current weather landscape image

```bash
curl https://weather-landscape-worker.YOUR-SUBDOMAIN.workers.dev/current.png > weather.png
```

### `GET /status`
Returns generation status and metadata

```bash
curl https://weather-landscape-worker.YOUR-SUBDOMAIN.workers.dev/status
```

Example response:
```json
{
  "status": {
    "lastSuccess": "2025-01-10T12:00:00Z",
    "lastError": null,
    "errorCount": 0
  },
  "metadata": {
    "generatedAt": "2025-01-10T12:00:00Z",
    "latitude": 52.196136,
    "longitude": 21.007963,
    "fileSize": 45678,
    "format": "PNG",
    "variant": "rgb_white"
  }
}
```

### `POST /generate`
Manually trigger image generation (for testing)

```bash
curl -X POST https://weather-landscape-worker.YOUR-SUBDOMAIN.workers.dev/generate
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

**Solution:** Make sure all Python files are in the correct structure:
```
weather_landscape/
├── src/
│   ├── index.py          # Worker entry point
│   └── requirements.txt  # Python dependencies
├── p_weather/            # Weather module (must be accessible)
├── configs.py            # Configuration classes
└── weather_landscape.py  # Main class
```

### Issue: Import errors with existing modules

**Solution:** The worker needs access to the parent directory modules. You may need to:
1. Copy necessary modules into `src/` directory, or
2. Ensure proper Python path configuration in the worker

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
