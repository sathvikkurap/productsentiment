#!/usr/bin/env sh
# Quick start: create venv, install deps, check config. Run from project root.
set -e
cd "$(dirname "$0")/.."

echo "Creating venv..."
python3 -m venv .venv
. .venv/bin/activate

echo "Installing dependencies..."
pip install -q -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example (add API keys there if needed)."
fi

echo ""
echo "Checking sources (python run.py --check)..."
python run.py --check

echo ""
echo "Quick start done. Try:"
echo "  source .venv/bin/activate   # if not already active"
echo "  python run.py 'Notion' --sources hackernews,duckduckgo --limit 20"
