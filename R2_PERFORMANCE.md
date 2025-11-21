# R2 Upload Performance Investigation

## Problem
R2 uploads taking ~1.5-1.7 seconds for 3KB PNG files from landscape-generator worker.

## Root Cause: Geographic Mismatch

**Identified via instrumentation:**
- Python bytes → Uint8Array conversion: **1ms** (negligible)
- R2.put() network call: **1715ms** (99.9% of time)

**Infrastructure mismatch:**
- Worker deployment: `default` (runs in SEA/WNAM - Western North America)
- R2 bucket jurisdiction: `ENAM` (Eastern North America)

**Result:** Every upload makes a cross-country roundtrip (~2,500 miles), adding massive latency.

## Solution Options

### Option 1: Move R2 Bucket to WNAM (Recommended)
Create new bucket in same region as worker:

```bash
# Create new WNAM bucket
wrangler r2 bucket create weather-landscapes-wnam --jurisdiction wnam

# Migrate existing data (if needed)
wrangler r2 object get weather-landscapes <key> | \
  wrangler r2 object put weather-landscapes-wnam <key>

# Update wrangler.toml
bucket_name = "weather-landscapes-wnam"
jurisdiction = "wnam"
```

**Expected improvement:** 1700ms → ~100-300ms (5-17x faster)

### Option 2: Deploy Worker to ENAM
Constrain worker to run only in Eastern North America:

```toml
# In wrangler.toml, add:
[placement]
mode = "smart"
```

Then use Cloudflare dashboard to set placement hints to prefer ENAM regions.

**Expected improvement:** Similar to Option 1

### Option 3: Accept Current Performance
If uploads are async and non-blocking, the latency may be acceptable.

## Code Optimizations Applied

Even though geographic mismatch is the main issue, we still improved the conversion:

**Before:**
```python
js_array = Uint8Array.new(len(image_bytes))
for i, byte in enumerate(image_bytes):  # 3,297 boundary crossings!
    js_array[i] = byte
```

**After:**
```python
js_array = Uint8Array.new(memoryview(image_bytes))  # Single bulk transfer
await env.WEATHER_IMAGES.put(key, js_array.buffer)
```

**Improvements:**
- Use `memoryview()` for efficient buffer protocol conversion
- Pass `ArrayBuffer` (via `.buffer`) instead of `Uint8Array` to R2
- Eliminates 3,000+ Python→JS boundary crossings

**Result:** Conversion time negligible (<1ms) regardless of file size.

## Performance Baseline

R2 PUT operations from Workers have inherent overhead:
- Reported minimum: ~400ms for small files (community reports)
- Cross-region penalty: +1,000-1,500ms (this case)
- Network latency: Depends on colo ↔ bucket distance

## Monitoring

The observability spans show the full picture:
```json
{
  "name": "r2_put",
  "duration": 1498,
  "durationMS": 1498
}
```

After moving bucket to WNAM, expect this to drop to 100-400ms range.

## References

- Cloudflare Community: Multiple reports of slow R2 PUTs
- Known baseline: 400ms+ per small file operation
- Geographic mismatch adds latency proportional to distance
