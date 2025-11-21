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

# Deploy all workers with delays to avoid rate limiting
echo "📦 Deploying workers..."

echo "Deploying web worker..."
uv run pywrangler deploy -c wrangler.local.toml
sleep 3

echo "Deploying job dispatcher..."
uv run pywrangler deploy -c wrangler.dispatcher.local.toml
sleep 3

echo "Deploying landscape generator..."
uv run pywrangler deploy -c wrangler.generator.local.toml
sleep 3

echo "Deploying zip scheduler (isolated environment)..."
(cd workers/scheduler && uv run pywrangler deploy -c wrangler.local.toml)
sleep 3

echo "Deploying weather fetcher (isolated environment)..."
(cd workers/fetcher && uv run pywrangler deploy -c wrangler.local.toml)

echo ""
echo "✅ All workers deployed successfully!"
