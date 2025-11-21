#!/bin/bash
# Setup script to generate local wrangler config files with your actual KV namespace IDs
# This allows you to keep the templates in git without exposing your namespace IDs

set -e

CONFIG_FILE=".wrangler.local.env"
EXAMPLE_FILE=".wrangler.local.env.example"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ $CONFIG_FILE not found!"
    echo "📝 Please copy $EXAMPLE_FILE to $CONFIG_FILE and fill in your values:"
    echo "   cp $EXAMPLE_FILE $CONFIG_FILE"
    echo "   # Edit $CONFIG_FILE with your actual KV namespace IDs"
    exit 1
fi

# Source the config
source "$CONFIG_FILE"

# Validate at least CONFIG is set
if [ -z "$CONFIG" ] || [ "$CONFIG" = "your_actual_kv_namespace_id_here" ]; then
    echo "❌ CONFIG binding not configured in $CONFIG_FILE"
    echo "📝 Please edit $CONFIG_FILE and set your actual KV namespace IDs"
    echo "   Example: CONFIG=abc123def456"
    exit 1
fi

echo "🔧 Generating local wrangler config files..."

# Array of wrangler config files (path:destination format for different directories)
CONFIGS=(
    "wrangler.toml"
    "wrangler.dispatcher.toml"
    "wrangler.generator.toml"
    "workers/scheduler/wrangler.toml"
    "workers/fetcher/wrangler.toml"
)

# Function to replace KV namespace IDs based on binding names
replace_kv_ids() {
    local input_file="$1"
    local output_file="$2"

    # Start with a copy of the input file
    cp "$input_file" "$output_file"

    # Read all binding=value pairs from .wrangler.local.env
    while IFS='=' read -r binding_name namespace_id; do
        # Skip comments and empty lines
        [[ "$binding_name" =~ ^#.*$ ]] && continue
        [[ -z "$binding_name" ]] && continue

        # Remove any whitespace
        binding_name=$(echo "$binding_name" | xargs)
        namespace_id=$(echo "$namespace_id" | xargs)

        # Skip if this is an example value
        [[ "$namespace_id" =~ your_actual.*here$ ]] && continue

        # Use awk to replace id = "YOUR_KV_NAMESPACE_ID" only where binding matches
        # This is a multi-line pattern match in awk
        awk -v binding="$binding_name" -v nsid="$namespace_id" '
        /\[\[kv_namespaces\]\]/ {
            in_kv_block = 1
            print
            next
        }
        in_kv_block && /^binding = / {
            print
            if ($0 ~ "\"" binding "\"") {
                found_binding = 1
            }
            next
        }
        in_kv_block && /^id = / && found_binding {
            print "id = \"" nsid "\""
            found_binding = 0
            in_kv_block = 0
            next
        }
        in_kv_block && /^\[/ {
            in_kv_block = 0
            found_binding = 0
        }
        { print }
        ' "$output_file" > "$output_file.tmp" && mv "$output_file.tmp" "$output_file"

    done < "$CONFIG_FILE"
}

# Generate local versions with actual values
for config in "${CONFIGS[@]}"; do
    if [ -f "$config" ]; then
        local_config="${config%.toml}.local.toml"
        replace_kv_ids "$config" "$local_config"
        echo "✅ Generated $local_config"
    else
        echo "⚠️  Warning: $config not found, skipping"
    fi
done

echo ""
echo "✨ Done! Local config files generated."
echo ""
echo "📦 To deploy, use the deploy-all.sh script or deploy individually:"
echo "   ./deploy-all.sh"
echo "   # OR deploy individually:"
echo "   uv run pywrangler deploy -c wrangler.local.toml"
echo "   (cd workers/fetcher && uv run pywrangler deploy -c wrangler.local.toml)"
echo "   etc."
echo ""
echo "💡 Tip: The *.local.toml files are git-ignored, so your namespace IDs stay private"
