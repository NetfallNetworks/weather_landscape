# R2 Bucket Migration: ENAM → WNAM

## Context
Worker runs consistently in SEA/WNAM region, but R2 bucket is in ENAM.
This causes ~1.7s cross-region latency for 3KB uploads.

## Migration Steps

### 1. Create New WNAM Bucket
```bash
wrangler r2 bucket create weather-landscapes-wnam --jurisdiction wnam
```

### 2. Update Worker Configuration
Update `workers/landscape/wrangler.toml`:
```toml
[[r2_buckets]]
binding = "WEATHER_IMAGES"
bucket_name = "weather-landscapes-wnam"
jurisdiction = "wnam"
```

### 3. Deploy Updated Worker
```bash
cd workers/landscape
wrangler deploy
```

### 4. Verify Performance
Check observability traces for `r2_put` span duration:
- **Before:** ~1700ms
- **Expected after:** ~100-300ms

### 5. Migrate Existing Data (Optional)
If you need to preserve existing images:

```bash
# List all objects in old bucket
wrangler r2 object list weather-landscapes

# Copy each object (example for one file)
wrangler r2 object get weather-landscapes 78729/rgb_light.png | \
  wrangler r2 object put weather-landscapes-wnam 78729/rgb_light.png
```

For bulk migration, consider using rclone or S3-compatible tools.

### 6. Cleanup Old Bucket (After Verification)
Once verified that new bucket works and data is migrated:
```bash
wrangler r2 bucket delete weather-landscapes
```

## Expected Improvement
- Upload latency: **1700ms → 100-300ms** (5-17x faster)
- Eliminates cross-country roundtrip (2500+ miles)
- Worker and bucket now co-located in WNAM region
