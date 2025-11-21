#!/bin/bash
# Deploy weather fetcher worker with venv cleanup
# This script ensures no venv gets bundled into the worker

set -e

echo "🧹 Cleaning up any virtual environments..."
rm -rf .venv .venv-workers venv env __pycache__

echo "🚀 Deploying weather fetcher worker..."
uv run pywrangler deploy -c wrangler.local.toml

echo "🧹 Post-deploy cleanup..."
rm -rf .venv .venv-workers venv env __pycache__

echo "✅ Weather fetcher deployed successfully!"
