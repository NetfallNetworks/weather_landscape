#!/bin/bash
# Deploy all workers using local configuration files
# Runs setup-local-config.sh first to ensure configs are up to date

set -e

echo "🚀 Deploying all workers..."
echo ""

# Ensure local configs are up to date
echo "📝 Regenerating local config files..."
./setup-local-config.sh
echo ""

# Deploy all workers
echo "📦 Deploying workers..."
uv run pywrangler deploy -c wrangler.local.toml && \
uv run pywrangler deploy -c wrangler.fetcher.local.toml && \
uv run pywrangler deploy -c wrangler.dispatcher.local.toml && \
uv run pywrangler deploy -c wrangler.generator.local.toml && \
uv run pywrangler deploy -c wrangler.scheduler.local.toml

echo ""
echo "✅ All workers deployed successfully!"
