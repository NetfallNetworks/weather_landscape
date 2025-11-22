# Recreate R2 Bucket Without Location Suffix

## Context
The bucket was initially created as `weather-landscapes-wnam` with the location encoded in the name.
Since location hints are just hints (not guarantees), encoding them in the bucket name isn't best practice.

## Migration Commands

### 1. Delete the temporary WNAM bucket
```bash
uv run pywrangler r2 bucket delete weather-landscapes-wnam
```

### 2. Create new bucket with proper name and location hint
```bash
uv run pywrangler r2 bucket create weather-landscapes --location wnam
```

### 3. Deploy updated workers
```bash
cd workers/landscape
uv run pywrangler deploy

cd ../web
uv run pywrangler deploy
```

### 4. Verify performance (should still be ~100-300ms)
Check observability traces for `r2_put` span duration.

## Notes
- Location hints are optimization suggestions, not guarantees
- Cloudflare may move data based on access patterns over time
- Bucket name should be stable and not encode transient configuration
