#!/bin/bash
# Purge all virtual environments from the fetcher worker directory

echo "🧹 Purging virtual environments from weather fetcher..."

# Remove all venv directories
rm -rf .venv .venv-workers venv env

# Remove Python cache
rm -rf __pycache__
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

echo "✅ Virtual environments purged!"
