#!/bin/bash
cd "$(dirname "$0")"

echo "=== Stopping any stale server on port 5001 ==="
lsof -ti :5001 | xargs kill -9 2>/dev/null
sleep 1

echo "=== Starting Catalog Manager on http://127.0.0.1:5001 ==="
python3 catalog_server.py 5001
