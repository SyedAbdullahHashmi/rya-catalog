#!/bin/bash
# Build catalogs from JSON with RYRA & CO. styling.
# Manually edited HTML files are backed up before build and restored after,
# so your customisations are never overwritten.

cd "$(dirname "$0")"

OUT_DIR="html_catalogs"
BACKUP_DIR="html_catalogs_manual_backup"
MANUAL_FILES=(
    "catalog_mens_accessories.html"
    "catalog_mens_jewelry.html"
    "catalog_womens_jewelry.html"
    "catalog_womens_clutches.html"
)

# 1. Back up any manually edited HTMLs that exist (fresh backup each run)
rm -rf "$BACKUP_DIR"
mkdir -p "$BACKUP_DIR"
for f in "${MANUAL_FILES[@]}"; do
    if [ -f "$OUT_DIR/$f" ]; then
        cp "$OUT_DIR/$f" "$BACKUP_DIR/$f"
        echo "Backed up: $f"
    fi
done

# 2. Regenerate all catalogs from JSON (RYRA & CO. styling)
python3 build_catalogs.py

# 3. Restore manually edited HTMLs so your edits survive the rebuild
for f in "${MANUAL_FILES[@]}"; do
    if [ -f "$BACKUP_DIR/$f" ]; then
        cp "$BACKUP_DIR/$f" "$OUT_DIR/$f"
        echo "Restored manual edit: $f"
    fi
done

echo ""
echo "Done. Manual edits preserved in: $BACKUP_DIR"
echo "To discard manual edits and use the generated version instead:"
echo "   rm -rf $BACKUP_DIR && ./build.sh"
