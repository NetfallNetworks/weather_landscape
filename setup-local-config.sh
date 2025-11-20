#!/bin/bash
# Setup script to generate local wrangler config files with your actual KV namespace ID
# This allows you to keep the templates in git without exposing your namespace ID

set -e

CONFIG_FILE=".wrangler.local.env"
EXAMPLE_FILE=".wrangler.local.env.example"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ $CONFIG_FILE not found!"
    echo "📝 Please copy $EXAMPLE_FILE to $CONFIG_FILE and fill in your values:"
    echo "   cp $EXAMPLE_FILE $CONFIG_FILE"
    echo "   # Edit $CONFIG_FILE with your actual KV namespace ID"
    exit 1
fi

# Source the config
source "$CONFIG_FILE"

# Validate KV_NAMESPACE_ID is set
if [ -z "$KV_NAMESPACE_ID" ] || [ "$KV_NAMESPACE_ID" = "your_actual_kv_namespace_id_here" ]; then
    echo "❌ KV_NAMESPACE_ID not configured in $CONFIG_FILE"
    echo "📝 Please edit $CONFIG_FILE and set your actual KV namespace ID"
    exit 1
fi

echo "🔧 Generating local wrangler config files..."

# Array of wrangler config files
CONFIGS=(
    "wrangler.toml"
    "wrangler.fetcher.toml"
    "wrangler.dispatcher.toml"
    "wrangler.generator.toml"
    "wrangler.scheduler.toml"
)

# Generate local versions with actual values
for config in "${CONFIGS[@]}"; do
    if [ -f "$config" ]; then
        local_config="${config%.toml}.local.toml"
        sed "s/YOUR_KV_NAMESPACE_ID/$KV_NAMESPACE_ID/g" "$config" > "$local_config"
        echo "✅ Generated $local_config"
    else
        echo "⚠️  Warning: $config not found, skipping"
    fi
done

echo ""
echo "✨ Done! Local config files generated."
echo ""
echo "📦 To deploy, use the -c flag with the local config:"
echo "   wrangler deploy -c wrangler.local.toml"
echo "   wrangler deploy -c wrangler.fetcher.local.toml"
echo "   etc."
echo ""
echo "💡 Tip: The *.local.toml files are git-ignored, so your namespace ID stays private"
