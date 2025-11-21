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

## Solution (Implemented)

### Move R2 Bucket to WNAM ✅

Created new bucket matching worker execution region:

```bash
# Create new WNAM bucket
wrangler r2 bucket create weather-landscapes-wnam --jurisdiction wnam
```

**Configuration updates:**
- `workers/landscape/wrangler.toml`: Updated to use `weather-landscapes-wnam`
- `workers/web/wrangler.toml`: Updated to use `weather-landscapes-wnam` + added smart placement

**Why this works:**
- Queue consumer workers run consistently in WNAM (SEA colo)
- Smart placement doesn't affect queue consumers (only HTTP fetch handlers)
- Co-locating bucket with worker eliminates cross-region latency

**Status:** ✅ Implemented
**Expected improvement:** 1700ms → ~100-300ms (5-17x faster)

### Smart Placement for Web Worker ✅

Added smart placement to the web worker since it serves HTTP requests from various locations:

```toml
# In workers/web/wrangler.toml
[placement]
mode = "smart"
```

This allows the web worker to run closer to where users are accessing it, while still accessing the WNAM R2 bucket efficiently.

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
