# Multi-ZIP Code Support Guide

This guide explains how to use the weather landscape worker with multiple ZIP codes.

## Overview

The worker now supports generating weather landscape images for multiple US ZIP codes simultaneously. Each ZIP code gets its own folder in R2 storage, and the system uses OpenWeatherMap's Geocoding API to convert ZIP codes to coordinates with efficient KV caching.

## Architecture

### Geocoding with KV Caching
- **API**: OpenWeatherMap Geocoding API (`http://api.openweathermap.org/geo/1.0/zip`)
- **Cache Key Pattern**: `geo:{ZIP}` (e.g., `geo:78729`)
- **Cache Format**:
  ```json
  {
    "lat": 30.4515,
    "lon": -97.7676,
    "zip": "78729",
    "cached_at": "2025-11-14T12:00:00Z"
  }
  ```
- **Cache Duration**: Forever (ZIP codes don't change location)
- **First Request**: Calls OWM Geocoding API and stores result
- **Subsequent Requests**: Uses cached coordinates from KV

### Active ZIP Codes List
- **KV Key**: `active_zips`
- **Format**: JSON array of ZIP code strings
- **Example**: `["78729", "90210", "10001"]`
- **Default**: `["78729"]` (Austin, TX)
- **Management**: Update via KV dashboard or API

### R2 Storage Structure
```
weather-landscapes/
├── 78729/
│   └── latest.png
├── 90210/
│   └── latest.png
└── 10001/
    └── latest.png
```

### KV Metadata Structure
- **Per-ZIP Metadata**: `metadata:{ZIP}` (e.g., `metadata:78729`)
- **Overall Status**: `status` (contains last run info, success/error counts)
- **Format**:
  ```json
  {
    "generatedAt": "2025-11-14T12:00:00Z",
    "latitude": 30.4515,
    "longitude": -97.7676,
    "zipCode": "78729",
    "fileSize": 12345,
    "format": "PNG",
    "variant": "rgb_white"
  }
  ```

## Scheduled Execution Flow

Every 15 minutes (or per your cron schedule):

1. **Load Active ZIPs**: Reads `active_zips` from KV
2. **For Each ZIP**:
   - Check KV for cached geocoding (`geo:{ZIP}`)
   - If not cached: call OWM Geocoding API and cache result
   - Use cached lat/lon to fetch weather from OWM
   - Generate landscape image
   - Upload to R2 as `{ZIP}/latest.png`
   - Store metadata in KV as `metadata:{ZIP}`
3. **Update Status**: Store overall run status in KV

## HTTP Endpoints

### Image Serving
- `GET /` - HTML page with default ZIP image
- `GET /latest.png` - Latest image for default ZIP (78729)
- `GET /{zip}/latest.png` - Latest image for specific ZIP (e.g., `/78729/latest.png`)
- `GET /current.png` - Backward compatible alias for `/latest.png`
- `GET /{zip}/current.png` - Backward compatible per-ZIP access

### Status and Control
- `GET /status` - Returns status for all active ZIPs
  ```json
  {
    "status": {
      "lastRun": "2025-11-14T12:00:00Z",
      "totalZips": 3,
      "successCount": 3,
      "errorCount": 0
    },
    "activeZips": ["78729", "90210", "10001"],
    "zipMetadata": {
      "78729": {...},
      "90210": {...},
      "10001": {...}
    },
    "workerTime": "2025-11-14T12:05:00Z"
  }
  ```

- `POST /generate?zip={ZIP}` - Manually trigger generation for specific ZIP
  - Example: `POST /generate?zip=90210`
  - Returns: `{"success": true, "zip": "90210", "metadata": {...}}`

## Managing Active ZIP Codes

### Via Wrangler CLI
```bash
# Add multiple ZIP codes
wrangler kv:key put --binding=CONFIG "active_zips" '["78729","90210","10001"]'

# Check current list
wrangler kv:key get --binding=CONFIG "active_zips"
```

### Via Cloudflare Dashboard
1. Go to Workers & Pages → KV
2. Select your `weather-config` namespace
3. Edit the `active_zips` key
4. Set value as JSON array: `["78729","90210","10001"]`

### Via API (using curl)
```bash
# Manually trigger generation for a new ZIP
curl -X POST https://your-worker.workers.dev/generate?zip=90210

# Check status
curl https://your-worker.workers.dev/status
```

## Adding a New ZIP Code

1. **Update KV**: Add the ZIP to the `active_zips` array
2. **Wait for Cron**: The next scheduled run will automatically:
   - Geocode the new ZIP (first time only)
   - Generate and upload the image
   - Store metadata
3. **Or Trigger Manually**:
   ```bash
   curl -X POST https://your-worker.workers.dev/generate?zip=NEW_ZIP
   ```

## Performance Considerations

- **First Run**: Calls OWM Geocoding API once per new ZIP
- **Subsequent Runs**: Uses cached coordinates (no extra API calls)
- **Multiple ZIPs**: Processed sequentially in each cron run
- **Cron Interval**: Default 15 minutes (adjust in `wrangler.toml`)

## Migration from Single-ZIP Setup

The system is backward compatible:
- `/current.png` still works (redirects to default ZIP's latest.png)
- Default ZIP is set in `wrangler.toml` as `DEFAULT_ZIP`
- If `active_zips` is not set, defaults to `["78729"]`

## Troubleshooting

### ZIP Not Generating
- Check `/status` endpoint for error details
- Verify ZIP is in `active_zips` list
- Check worker logs for geocoding errors

### Geocoding Failures
- Verify OWM API key is valid
- Check that ZIP code is valid US ZIP
- OWM Geocoding API rate limits: 60 calls/minute (should not be an issue with caching)

### R2 Storage Not Found
- First generation may take up to 15 minutes
- Manually trigger: `POST /generate?zip=YOUR_ZIP`
- Check worker logs for upload errors

## Example Usage

```bash
# Add three ZIP codes
wrangler kv:key put --binding=CONFIG "active_zips" '["78729","94102","10001"]'

# Wait for next cron run (or trigger manually)
curl -X POST https://your-worker.workers.dev/generate?zip=94102

# Check status
curl https://your-worker.workers.dev/status

# Access specific ZIP's image
curl https://your-worker.workers.dev/78729/latest.png > austin.png
curl https://your-worker.workers.dev/94102/latest.png > san-francisco.png
curl https://your-worker.workers.dev/10001/latest.png > new-york.png
```

## Cost Considerations

- **OWM Geocoding API**: Free tier includes 1,000 calls/day
  - With caching, only called once per new ZIP
  - Example: 100 new ZIPs = 100 API calls (one-time)

- **OWM Weather API**: Free tier includes 1,000 calls/day
  - Called every 15 minutes per ZIP
  - Example: 3 ZIPs × 4 calls/hour × 24 hours = 288 calls/day

- **R2 Storage**:
  - Each ZIP: ~10-50 KB per image
  - 100 ZIPs = ~5 MB total storage
  - Very low cost

- **KV Operations**:
  - Geocoding cache: Read-heavy after initial setup
  - Metadata: Write on each generation
  - Well within free tier limits
