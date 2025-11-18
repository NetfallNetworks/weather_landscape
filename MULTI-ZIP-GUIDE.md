# Multi-ZIP Code Weather Landscape

Complete guide for the multi-ZIP code weather landscape worker running on Cloudflare.

## Quick Start

The worker automatically generates weather landscape images for multiple US ZIP codes. Each ZIP gets its own image stored in R2 at `{ZIP}/latest.png`.

### Architecture

```
Cloudflare Worker (Python)
├── Cron: Every 15 minutes
├── For each active ZIP:
│   ├── Geocode ZIP → lat/lon (cached in KV)
│   ├── Fetch weather from OpenWeatherMap
│   ├── Generate landscape PNG
│   └── Upload to R2 at {ZIP}/latest.png
└── Update status in KV
```

### Storage Structure

**R2 Bucket: `weather-landscapes`**
```
weather-landscapes/
├── 78729/
│   └── latest.png
├── 90210/
│   └── latest.png
└── 10001/
    └── latest.png
```

**KV Namespace: `weather-config`**
```
active_zips          → ["78729", "90210", "10001"]
geo:78729            → {"lat": 30.4515, "lon": -97.7676, ...}
geo:90210            → {"lat": 34.0901, "lon": -118.4065, ...}
metadata:78729       → {"generatedAt": "...", "latitude": 30.4515, ...}
status               → {"lastRun": "...", "successCount": 3, ...}
```

## Web Interface

### Public Pages

**`GET /`** - Landing Page
Welcome page with project explanation, examples, and quick decoder

**`GET /forecasts`** - Forecasts Page
Card-based interface showing all configured ZIP codes with:
- Status badges (✓ Up to date / ○ Not updating)
- Clickable format buttons for each available format
- Responsive grid layout

**`GET /guide`** - Reading Guide
Comprehensive guide with live examples and detailed explanations

**`GET /admin`** - Admin Dashboard
Web interface for managing ZIP codes:
- View all ZIP codes (both active and in R2)
- Toggle active/inactive status with switches
- Manage formats with checkboxes
- Add new ZIP codes via form
- Manually trigger generation with "Generate Now" button

### Image Access

**`GET /{zip}`** - Get latest image for specific ZIP (default format)

```bash
curl https://your-worker.workers.dev/78729 > austin.png
```

**`GET /{zip}?{format}`** - Get specific format

```bash
# Get dark theme
curl https://your-worker.workers.dev/78729?rgb_dark > austin_dark.png

# Get E-Ink version
curl https://your-worker.workers.dev/78729?eink > austin_eink.bmp
```

Response headers:
- `Content-Type: image/png` (or `image/bmp` for BW formats)
- `X-Generated-At: 2025-11-14T12:00:00Z`
- `X-Zip-Code: 78729`
- `Cache-Control: public, max-age=900`

### Status & Control

**`GET /status`** - View status for all active ZIPs

```bash
curl https://your-worker.workers.dev/status
```

Response:
```json
{
  "status": {
    "lastRun": "2025-11-14T12:00:00Z",
    "totalZips": 3,
    "successCount": 3,
    "errorCount": 0,
    "errors": null
  },
  "activeZips": ["78729", "90210", "10001"],
  "zipMetadata": {
    "78729": {
      "generatedAt": "2025-11-14T12:00:00Z",
      "latitude": 30.4515,
      "longitude": -97.7676,
      "zipCode": "78729",
      "fileSize": 12345,
      "format": "PNG",
      "variant": "rgb_white"
    },
    ...
  },
  "workerTime": "2025-11-14T12:05:00Z"
}
```

**`POST /generate?zip={zip}`** - Manually trigger generation

```bash
# Generate for specific ZIP
curl -X POST https://your-worker.workers.dev/generate?zip=90210

# Response
{"success": true, "zip": "90210", "metadata": {...}}
```

**`GET /`** - Info page with links to all active ZIPs

Shows clickable links to all active ZIP codes and API documentation.

## Managing Active ZIP Codes

### Via Admin Dashboard (Recommended)

The easiest way to manage ZIP codes is through the web UI at `/admin`:

1. **View all ZIPs**: See both active (in KV) and available (in R2)
2. **Toggle active status**: Click the switch next to any ZIP to activate/deactivate
3. **Add new ZIP**: Use the "Add New ZIP Code" form at the top
4. **Manage formats**: Check/uncheck format boxes for each ZIP
5. **Generate now**: Click button to immediately trigger generation

### Via API

```bash
# Activate a ZIP (adds to active_zips in KV)
curl -X POST https://your-worker.workers.dev/admin/activate?zip=78729

# Deactivate a ZIP (removes from active_zips)
curl -X POST https://your-worker.workers.dev/admin/deactivate?zip=78729

# Trigger generation for a ZIP (also adds to geocoding cache)
curl -X POST https://your-worker.workers.dev/admin/generate?zip=02134
```

### Via Wrangler CLI

```bash
# View current active ZIPs
wrangler kv:key get --binding=CONFIG "active_zips"

# Set ZIPs (replaces entire list)
wrangler kv:key put --binding=CONFIG "active_zips" '["78729","90210","10001","02134"]'
```

### Via Cloudflare Dashboard

1. Navigate to **Workers & Pages** → **KV**
2. Select your `CONFIG` namespace
3. Find the `active_zips` key
4. Edit value: `["78729","90210","10001"]`
5. Save

## Geocoding with KV Caching

### How It Works

1. **First request for a ZIP:**
   - Calls OpenWeatherMap Geocoding API
   - Gets lat/lon coordinates
   - Stores in KV as `geo:{ZIP}`
   - Cache never expires (ZIP locations don't change)

2. **Subsequent requests:**
   - Reads from KV cache
   - No API call needed
   - Instant lookup

### Cache Format

**KV Key:** `geo:78729`

**Value:**
```json
{
  "lat": 30.4515,
  "lon": -97.7676,
  "zip": "78729",
  "cached_at": "2025-11-14T10:00:00Z"
}
```

### Manual Cache Management

```bash
# View cached geocoding for a ZIP
wrangler kv:key get --binding=CONFIG "geo:78729"

# Clear cache for a ZIP (will re-geocode on next run)
wrangler kv:key delete --binding=CONFIG "geo:78729"

# Clear all geocoding cache
wrangler kv:key list --binding=CONFIG --prefix="geo:" | \
  jq -r '.[].name' | \
  xargs -I {} wrangler kv:key delete --binding=CONFIG "{}"
```

## Scheduled Execution

The worker runs every 15 minutes (configurable in `wrangler.toml`):

```toml
[triggers]
crons = ["*/15 * * * *"]  # Every 15 minutes
```

### Execution Flow

```
1. Load active_zips from KV → ["78729", "90210", "10001"]
2. For each ZIP:
   a. Check geo:{ZIP} in KV
   b. If not cached: Call OWM Geocoding API, store in KV
   c. Use lat/lon to fetch weather from OWM
   d. Generate landscape image (296x128 PNG)
   e. Upload to R2: {ZIP}/latest.png
   f. Store metadata in KV: metadata:{ZIP}
   g. Log success/failure
3. Update overall status in KV
4. Log summary: X success, Y errors
```

### Logs

View worker logs:
```bash
wrangler tail
```

Example output:
```
🕐 Scheduled run started at 2025-11-14T12:00:00.000Z
📋 Processing 3 ZIP code(s): 78729, 90210, 10001

🔄 Processing ZIP 78729...
📍 Using cached geocoding for 78729: 30.4515, -97.7676
🎨 Generating weather landscape for 78729...
☁️  Uploading 78729 to R2...
✅ Uploaded 78729/latest.png to R2 (12345 bytes)
✅ Completed 78729

🔄 Processing ZIP 90210...
🌐 Geocoding ZIP 90210 via OWM API...
✅ Cached geocoding for 90210: 34.0901, -118.4065
🎨 Generating weather landscape for 90210...
☁️  Uploading 90210 to R2...
✅ Uploaded 90210/latest.png to R2 (11234 bytes)
✅ Completed 90210

...

✅ Scheduled run completed: 3 success, 0 errors
```

## Configuration

### Environment Variables

Set in `wrangler.toml`:

```toml
[vars]
DEFAULT_LAT = 30.4515        # Fallback latitude (Austin, TX)
DEFAULT_LON = -97.7676       # Fallback longitude
DEFAULT_ZIP = "78729"        # Default ZIP code
IMAGE_WIDTH = 296            # Image width in pixels
IMAGE_HEIGHT = 128           # Image height in pixels
UPDATE_INTERVAL_MINUTES = 15 # Cron interval
```

### Secrets

Set via Wrangler (NOT in wrangler.toml):

```bash
# OpenWeatherMap API key (required)
wrangler secret put OWM_API_KEY
```

## API Costs & Limits

### OpenWeatherMap Free Tier

- **Weather API:** 1,000 calls/day
- **Geocoding API:** 1,000 calls/day

### Our Usage

**With 3 active ZIPs:**
- Weather calls: 3 ZIPs × 4 calls/hour × 24 hours = **288/day** ✅
- Geocoding calls: One-time per new ZIP (then cached)

**With 10 active ZIPs:**
- Weather calls: 10 ZIPs × 4 calls/hour × 24 hours = **960/day** ✅
- Still within free tier!

**With 20 active ZIPs:**
- Weather calls: 20 ZIPs × 4 calls/hour × 24 hours = **1,920/day** ⚠️
- Exceeds free tier - need paid plan or reduce frequency

### Cloudflare Free Tier

**R2 Storage:**
- 10 GB storage/month
- Our usage: ~30 KB/image × 20 ZIPs = **600 KB** ✅

**KV Operations:**
- 100,000 reads/day
- 1,000 writes/day
- Our usage: ~100 reads/day, ~100 writes/day ✅

**Workers Requests:**
- 100,000 requests/day
- Our usage: Cron only (96/day) + manual requests ✅

## Troubleshooting

### ZIP not generating

1. Check if ZIP is in active_zips:
   ```bash
   wrangler kv:key get --binding=CONFIG "active_zips"
   ```

2. View logs for errors:
   ```bash
   wrangler tail
   ```

3. Check status endpoint:
   ```bash
   curl https://your-worker.workers.dev/status | jq '.status.errors'
   ```

4. Manually trigger to see error:
   ```bash
   curl -X POST https://your-worker.workers.dev/generate?zip=78729
   ```

### Geocoding failures

- **Invalid ZIP:** OWM returns 404 for non-existent ZIPs
- **API key invalid:** Check `wrangler secret list`
- **Rate limit:** Wait and retry, cache will prevent future calls

### Image not found (404)

- **First generation:** Wait up to 15 minutes for cron
- **Missing from active_zips:** Add ZIP to list
- **Generation failed:** Check logs for error

### Out-of-date images

- Images update every 15 minutes
- Check `X-Generated-At` header on image response
- Manually trigger: `POST /generate?zip={zip}`

## Advanced Usage

### Different Cron Schedules

```toml
# Every 5 minutes (more API calls!)
crons = ["*/5 * * * *"]

# Every hour (fewer API calls)
crons = ["0 * * * *"]

# Every 30 minutes
crons = ["*/30 * * * *"]

# Specific times only (e.g., hourly during day)
crons = ["0 6-22 * * *"]  # Every hour from 6am-10pm
```

### Batch Add Multiple ZIPs

```bash
# Create list of ZIPs
cat > zips.json <<EOF
["78729","90210","10001","02134","60601","94102","98101"]
EOF

# Upload to KV
wrangler kv:key put --binding=CONFIG "active_zips" "$(cat zips.json)"

# Verify
wrangler kv:key get --binding=CONFIG "active_zips"
```

### Export All Images

```bash
# Download all images for all active ZIPs
ACTIVE_ZIPS=$(curl -s https://your-worker.workers.dev/status | jq -r '.activeZips[]')

for zip in $ACTIVE_ZIPS; do
  curl "https://your-worker.workers.dev/$zip/latest.png" > "$zip.png"
  echo "Downloaded $zip.png"
done
```

### Monitor Generation Status

```bash
# Check status every minute
watch -n 60 'curl -s https://your-worker.workers.dev/status | jq ".status"'
```

## Migration Notes

### From Single ZIP Setup

The system automatically migrates:
- If `active_zips` not in KV → creates `["78729"]`
- Old images continue working (if manually placed at `{ZIP}/latest.png`)
- No code changes needed

### Adding New ZIPs

1. Update `active_zips` in KV
2. Wait for next cron run (auto-generates)
3. Or manually trigger: `POST /generate?zip={new_zip}`

## Development

### Local Testing

```bash
# Test generation locally (requires OWM API key in secrets.py)
uv run python test_local_generation.py
```

### Deploy Changes

```bash
# Deploy to Cloudflare
wrangler deploy

# View logs
wrangler tail
```

### Test Endpoints

```bash
# Root page
curl https://your-worker.workers.dev/

# Specific ZIP image
curl https://your-worker.workers.dev/78729/latest.png -I

# Status
curl https://your-worker.workers.dev/status | jq

# Manual generation
curl -X POST https://your-worker.workers.dev/generate?zip=78729 | jq
```

## Support

For issues or questions:
1. Check worker logs: `wrangler tail`
2. Check status endpoint: `GET /status`
3. Review this guide
4. Check OpenWeatherMap API status
