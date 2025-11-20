# Local Development Setup

## Wrangler Configuration

This project uses a template-based approach for Wrangler configuration files to keep sensitive IDs out of version control.

### Initial Setup

1. **Copy the example config file:**
   ```bash
   cp .wrangler.local.env.example .wrangler.local.env
   ```

2. **Add your KV namespace ID:**
   Edit `.wrangler.local.env` and replace `your_actual_kv_namespace_id_here` with your actual KV namespace ID.

   To find your KV namespace ID:
   ```bash
   wrangler kv namespace list
   ```

3. **Generate local config files:**
   ```bash
   ./setup-local-config.sh
   ```

   This creates `*.local.toml` files with your actual KV namespace ID. These files are git-ignored.

### Deploying Workers

Use the `-c` flag to deploy with your local config:

```bash
# Deploy web worker
wrangler deploy -c wrangler.local.toml

# Deploy fetcher worker
wrangler deploy -c wrangler.fetcher.local.toml

# Deploy dispatcher worker
wrangler deploy -c wrangler.dispatcher.local.toml

# Deploy generator worker
wrangler deploy -c wrangler.generator.local.toml

# Deploy scheduler worker
wrangler deploy -c wrangler.scheduler.local.toml
```

### How It Works

- **Template files** (`wrangler.toml`, `wrangler.fetcher.toml`, etc.) contain `YOUR_KV_NAMESPACE_ID` as a placeholder and are committed to git
- **Local config** (`.wrangler.local.env`) contains your actual IDs and is git-ignored
- **Setup script** (`setup-local-config.sh`) generates local versions with real values
- **Local files** (`*.local.toml`) are used for deployment and are git-ignored

### Benefits

- ✅ No more manual stashing/unstashing when pulling changes
- ✅ Sensitive IDs stay out of version control
- ✅ Template files in git show configuration structure
- ✅ Easy onboarding for new developers

### After Pulling Changes

When you pull changes that modify wrangler files, simply run:

```bash
./setup-local-config.sh
```

This regenerates your local config files with the updated templates.
