#!/usr/bin/env python3
"""Merge new products from the zip into the existing RYRA & CO. catalogs.
Filters test/demo products, assigns categories, copies new images, rebuilds HTML."""

import hashlib
import json
import os
import shutil
import re

BASE_DIR = "/Users/syedabdullah.hashmi/Desktop/html catalogger"
ZIP_IMG_DIR = "/tmp/catalog_extract/html catalogger 2/images"
EXISTING_IMG_DIR = os.path.join(BASE_DIR, "images")
CATALOGS_DIR = os.path.join(BASE_DIR, "catalogs")
HTML_CATALOGS_DIR = os.path.join(BASE_DIR, "html_catalogs")

# --- Step 1: Copy new images that don't already exist ---
print("=== Step 1: Copying new images ===")
copied = 0
if os.path.isdir(ZIP_IMG_DIR):
    for fname in os.listdir(ZIP_IMG_DIR):
        src = os.path.join(ZIP_IMG_DIR, fname)
        dst = os.path.join(EXISTING_IMG_DIR, fname)
        if os.path.isfile(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
            copied += 1
    print(f"Copied {copied} new images to {EXISTING_IMG_DIR}")
else:
    print(f"WARNING: Image dir not found: {ZIP_IMG_DIR}")

# --- Step 2: Define catalog configs ---
CATALOG_CONFIGS = {
    "mens_jewelry": {
        "zip_path": os.path.join(ZIP_IMG_DIR, "..", "catalogs", "mens_jewelry.json"),
        "category_rules": [
            (r"(?i)\bbracelet\b", "Bracelets"),
            (r"(?i)\bearring\b", "Earrings"),
            (r"(?i)\bnecklace\b", "Necklaces"),
            (r"(?i)\bchain\b", "Necklaces"),
            (r"(?i)\bring\b", "Rings"),
        ],
    },
    "mens_accessories": {
        "zip_path": os.path.join(ZIP_IMG_DIR, "..", "catalogs", "mens_accessories.json"),
        "category_rules": [
            (r"(?i)\bnecklace\b", "Necklaces"),
            (r"(?i)\bpendant\b", "Necklaces"),
            (r"(?i)\bchain\b", "Necklaces"),
        ],
    },
    "womens_jewelry": {
        "zip_path": os.path.join(ZIP_IMG_DIR, "..", "catalogs", "womens_jewelry.json"),
        "category_rules": [
            (r"(?i)\bearring\b", "Earrings"),
            (r"(?i)\bhoop\b", "Earrings"),
            (r"(?i)\bstud\b", "Earrings"),
            (r"(?i)\bnecklace\b", "Necklaces"),
            (r"(?i)\bpendant\b", "Necklaces"),
            (r"(?i)\bring\b", "Rings"),
            (r"(?i)\bbracelet\b", "Bracelets"),
        ],
    },
    "womens_clutches": {
        "zip_path": os.path.join(ZIP_IMG_DIR, "..", "catalogs", "womens_clutches.json"),
        "category_rules": [
            (r"(?i)\bclutch\b", "Clutches"),
            (r"(?i)\bbag\b", "Clutches"),
            (r"(?i)\bcrossbody\b", "Clutches"),
        ],
    },
}

# --- Step 3: Helper functions ---
def is_test_product(product):
    """Filter out test/demo/placeholder products."""
    sku = (product.get("sku") or "").strip().upper()
    name = (product.get("name") or "").strip()
    # Non-RY SKUs that are clearly test data
    if sku in ("OIYO", "KUOI", "MAC-001"):
        return True
    # SKUs that are just "Test" or "test" with no real SKU pattern
    if name.strip().lower() == "test" and not re.match(r"^RY\d+$", sku):
        return True
    # Demo product prefixes
    if re.match(r"^(SC-|MEB-|MC-|CT-|MG-|GHE-|PN-)\d+$", sku):
        return True
    return False

def clean_price(price):
    """Normalize price to Rs. format."""
    price = (price or "").strip()
    if not price:
        return "Rs. 0"
    # Already has Rs. prefix
    if price.startswith("Rs."):
        # Fix malformed like "Rs.6199" -> "Rs. 6199"
        cleaned = re.sub(r"^Rs\.\s*(\d+[,\d]*\.?\d*)\s*$", r"Rs. \1", price)
        return cleaned
    # Has Rs. somewhere in the middle (malformed)
    m = re.search(r"Rs\.\s*(\d+[,\d]*\.?\d*)", price)
    if m:
        return f"Rs. {m.group(1)}"
    # Plain number — add Rs. prefix
    m = re.match(r"^(\d+[,\d]*\.?\d*)\s*$", price)
    if m:
        return f"Rs. {m.group(1)}"
    # Fallback — keep as-is but clean
    return price

def assign_category(name, rules):
    """Assign category based on keyword rules."""
    if not name:
        return "Other"
    for pattern, category in rules:
        if re.search(pattern, name):
            return category
    return "Other"

def load_json(path):
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"name": "", "products": []}

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

# --- Step 4: Process each catalog ---
print("\n=== Step 2: Merging catalogs ===")
for catalog_name, config in CATALOG_CONFIGS.items():
    zip_json_path = config["zip_path"]
    existing_json_path = os.path.join(CATALOGS_DIR, f"{catalog_name}.json")

    # Load existing
    existing = load_json(existing_json_path)
    existing_products = existing.get("products", [])
    existing_by_sku = {p.get("sku", "").strip().upper(): p for p in existing_products}

    # Load new from zip
    new_data = load_json(zip_json_path)
    new_products = new_data.get("products", [])

    # Filter test products
    filtered = [p for p in new_products if not is_test_product(p)]
    print(f"\n  {catalog_name}: {len(new_products)} total -> {len(filtered)} after test filter")

    # Deduplicate by SKU — build final list from merged_by_sku
    # Preserves order: existing products first (original order), then new ones
    merged_by_sku = dict(existing_by_sku)  # start with existing
    for p in filtered:
        sku = p.get("sku", "").strip().upper()
        if not sku:
            continue
        # Clean price
        p["price"] = clean_price(p.get("price", ""))
        # Assign category if missing
        if not p.get("category"):
            p["category"] = assign_category(p.get("name", ""), config["category_rules"])
        # Replace existing entry only if new data is better (has image, etc.)
        if sku in merged_by_sku:
            existing_p = merged_by_sku[sku]
            new_img = (p.get("image") or "").strip()
            old_img = (existing_p.get("image") or "").strip()
            if new_img and not old_img:
                merged_by_sku[sku] = p  # new version has image, use it
            # Otherwise keep existing (preserves category assignment)
        else:
            merged_by_sku[sku] = p

    # Build final ordered list
    final_products = list(merged_by_sku.values())

    merged_data = {
        "name": new_data.get("name", existing.get("name", catalog_name.replace("_", " ").title())),
        "products": final_products,
    }

    save_json(existing_json_path, merged_data)
    print(f"  Written: {existing_json_path} ({len(final_products)} products)")

# --- Step 5: Rebuild HTML ---
print("\n=== Step 3: Rebuilding HTML catalogs ===")
import subprocess
result = subprocess.run(
    ["python3", os.path.join(BASE_DIR, "build_catalogs.py")],
    cwd=BASE_DIR,
    capture_output=True,
    text=True,
)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)

print("\n=== Done ===")
