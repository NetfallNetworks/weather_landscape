# R2 Bucket Migration: ENAM → WNAM

## Context
Worker runs consistently in SEA/WNAM region, but R2 bucket was in ENAM.
This caused ~1.7s cross-region latency for 3KB uploads.

## Migration Steps

### 1. Create New WNAM Bucket ✅
```bash
uv run pywrangler r2 bucket create weather-landscapes-wnam --jurisdiction wnam
```
**Status:** ✅ Complete

### 2. Configuration Already Updated ✅
Both workers are configured to use the new bucket:
- `workers/landscape/wrangler.toml`: Uses `weather-landscapes-wnam`
- `workers/web/wrangler.toml`: Uses `weather-landscapes-wnam`

**Status:** ✅ Complete

### 3. Deploy Updated Workers
```bash
cd workers/landscape
uv run pywrangler deploy

cd ../web
uv run pywrangler deploy
```

### 4. Verify Performance
Check observability traces for `r2_put` span duration:
- **Before:** ~1700ms
- **Expected after:** ~100-300ms

### 5. Migrate Existing Data (Optional)
If you need to preserve existing images from the old ENAM bucket:

```bash
# List all objects in old bucket
uv run pywrangler r2 object list weather-landscapes

# Copy each object (example for one file)
uv run pywrangler r2 object get weather-landscapes 78729/rgb_light.png | \
  uv run pywrangler r2 object put weather-landscapes-wnam 78729/rgb_light.png
```

For bulk migration, consider using rclone or S3-compatible tools.

### 6. Cleanup Old Bucket (After Verification)
Once verified that new bucket works and data is migrated (if needed):
```bash
uv run pywrangler r2 bucket delete weather-landscapes
```

## Expected Improvement
- Upload latency: **1700ms → 100-300ms** (5-17x faster)
- Eliminates cross-country roundtrip (2500+ miles)
- Worker and bucket now co-located in WNAM region
