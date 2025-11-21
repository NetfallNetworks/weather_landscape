# Local Development Setup

## Wrangler Configuration

This project uses a template-based approach for Wrangler configuration files to keep sensitive IDs out of version control.

### Initial Setup

1. **Copy the example config file:**
   ```bash
   cp .wrangler.local.env.example .wrangler.local.env
   ```

2. **Add your KV namespace IDs:**
   Edit `.wrangler.local.env` and add your actual namespace IDs using `BINDING=id` format:

   ```bash
   # KV Namespace for configuration and metadata (used by all workers)
   CONFIG=your_actual_kv_namespace_id_here

   # Add additional KV namespaces as needed
   # RESULTS=another_namespace_id_here
   ```

   To find your KV namespace IDs:
   ```bash
   wrangler kv namespace list
   ```

   The binding name (e.g., `CONFIG`) should match the `binding = "CONFIG"` in your wrangler.toml files.

3. **Generate local config files:**
   ```bash
   ./setup-local-config.sh
   ```

   This creates `*.local.toml` files with your actual KV namespace IDs substituted. These files are git-ignored.

### Deploying Workers

**Deploy all workers at once:**
```bash
./deploy-all.sh
```

**Or deploy individually with the `-c` flag:**

```bash
# Deploy web worker
uv run pywrangler deploy -c wrangler.local.toml

# Deploy scheduler worker (isolated environment)
(cd workers/scheduler && uv run pywrangler deploy -c wrangler.local.toml)

# Deploy fetcher worker (isolated environment)
(cd workers/fetcher && uv run pywrangler deploy -c wrangler.local.toml)

# Deploy dispatcher worker (isolated environment)
(cd workers/dispatcher && uv run pywrangler deploy -c wrangler.local.toml)

# Deploy generator worker (isolated environment)
(cd workers/landscape && uv run pywrangler deploy -c wrangler.local.toml)
```

### How It Works

- **Template files** (`wrangler.toml`, `wrangler.fetcher.toml`, etc.) contain `YOUR_KV_NAMESPACE_ID` as a placeholder and are committed to git
- **Local config** (`.wrangler.local.env`) contains your actual IDs mapped by binding name (e.g., `CONFIG=abc123`) and is git-ignored
- **Setup script** (`setup-local-config.sh`) generates local versions by matching bindings to IDs and substituting values
- **Local files** (`*.local.toml`) are used for deployment and are git-ignored
- **Deploy script** (`deploy-all.sh`) regenerates configs and deploys all workers in sequence

### Benefits

- ✅ No more manual stashing/unstashing when pulling changes
- ✅ Sensitive IDs stay out of version control
- ✅ Binding-based mapping supports multiple KV namespaces per worker
- ✅ Template files in git show configuration structure
- ✅ Easy onboarding for new developers
- ✅ One-command deployment with `./deploy-all.sh`

### After Pulling Changes

When you pull changes that modify wrangler files, simply run:

```bash
./setup-local-config.sh
```

This regenerates your local config files with the updated templates.

### Adding New KV Namespaces

If you add a new KV namespace to a worker:

1. Add the binding to your wrangler.toml:
   ```toml
   [[kv_namespaces]]
   binding = "RESULTS"
   id = "YOUR_KV_NAMESPACE_ID"
   ```

2. Add the mapping to `.wrangler.local.env`:
   ```bash
   RESULTS=your_results_namespace_id_here
   ```

3. Regenerate local configs:
   ```bash
   ./setup-local-config.sh
   ```

The script will automatically substitute the correct ID based on the binding name.
