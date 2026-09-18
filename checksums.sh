#!/bin/bash
# Generate a checksum file for all HTML catalogs
cd "$(dirname "$0")"
for f in html_catalogs/catalog_*.html; do
    md5 -q "$f"
done
