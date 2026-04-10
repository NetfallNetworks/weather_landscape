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
# Clean stale venvs first — on WSL + Windows/OneDrive, cached venvs can have
# baked-in shebangs that point to a different path than the current working
# directory (e.g. OneDrive/Documents vs Documents), causing "python: not found".
echo "🧹 Cleaning stale virtual environments..."
for dir in workers/web workers/landscape workers/scheduler workers/fetcher workers/dispatcher; do
    rm -rf "$dir/.venv"
done

echo "📦 Deploying workers..."

echo "Deploying web worker (isolated environment)..."
(cd workers/web && uv run pywrangler deploy -c wrangler.local.toml)
sleep 3

echo "Deploying landscape generator (isolated environment)..."
(cd workers/landscape && uv run pywrangler deploy -c wrangler.local.toml)
sleep 3

echo "Deploying zip scheduler (isolated environment)..."
(cd workers/scheduler && uv run pywrangler deploy -c wrangler.local.toml)
sleep 3

echo "Deploying weather fetcher (isolated environment)..."
(cd workers/fetcher && uv run pywrangler deploy -c wrangler.local.toml)
sleep 3

echo "Deploying job dispatcher (isolated environment)..."
(cd workers/dispatcher && uv run pywrangler deploy -c wrangler.local.toml)

echo ""
echo "✅ All workers deployed successfully!"
