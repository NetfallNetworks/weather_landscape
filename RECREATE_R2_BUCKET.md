# Recreate R2 Bucket With Fresh Name

## Context
**IMPORTANT:** R2 location hints are only honored the FIRST time a bucket name is created.
If you delete and recreate a bucket with the same name, Cloudflare ignores the new location
hint and uses the original location.

Since `weather-landscapes` was originally created in ENAM, it will ALWAYS be recreated in
ENAM regardless of the `--location` flag. We need a completely new bucket name.

## Migration Commands

### 1. Delete existing buckets
```bash
uv run pywrangler r2 bucket delete weather-landscapes
uv run pywrangler r2 bucket delete weather-landscapes-wnam
```

### 2. Create bucket with NEW name (never used before)
```bash
uv run pywrangler r2 bucket create weather-landscape-images --location wnam
```

**Note:** The bucket name `weather-landscape-images` has never been used, so the location
hint will be respected.

### 3. Deploy updated workers
```bash
cd workers/landscape
uv run pywrangler deploy

cd ../web
uv run pywrangler deploy
```

### 4. Verify performance (should be ~100-300ms)
Check observability traces for `r2_put` span duration.

## Why This Happens

This is a known Cloudflare R2 behavior: location hints are "sticky" to bucket names.
Once a bucket name has been created in a location, that association is permanent,
even after deletion.

**References:**
- [GitHub Issue #465](https://github.com/pulumi/pulumi-cloudflare/issues/465)
- [GitHub Issue #3311](https://github.com/cloudflare/terraform-provider-cloudflare/issues/3311)
