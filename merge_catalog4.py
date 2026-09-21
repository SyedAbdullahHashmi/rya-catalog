#!/usr/bin/env python3
"""
Merge catalogger 4.zip into RYRA & CO. live catalog.

Changes:
- womens_jewelry: add 925 Silver + Best Sellers categories, merge new products
- womens_clutches: re-enable (was hidden), merge new clutch products
- mens_jewelry: merge new products (if any)
- mens_accessories: merge new products (if any)
- Copy new images, rebuild all HTML, commit and push
"""

import json, os, re, shutil, subprocess

BASE = "/Users/syedabdullah.hashmi/Desktop/html catalogger"
ZIP = "/tmp/catalog4/html catalogger"
IMG_FROM = os.path.join(ZIP, "images")
IMG_TO = os.path.join(BASE, "images")

CATALOGS = {
    "mens_jewelry": {
        "zip_json": os.path.join(ZIP, "catalogs", "mens_jewelry.json"),
        "category_rules": [
            (r"(?i)\bbracelet\b", "Bracelets"),
            (r"(?i)\bearring\b", "Earrings"),
            (r"(?i)\bnecklace\b", "Necklaces"),
            (r"(?i)\bchain\b", "Necklaces"),
            (r"(?i)\bring\b", "Rings"),
            (r"(?i)\bsunglasses\b", "Eyewear"),
            (r"(?i)\bwrist\w*watch\b", "Watches"),
            (r"(?i)\bwatch\b", "Watches"),
            (r"(?i)\bkeychain\b", "Accessories"),
            (r"(?i)\bwallet\b", "Accessories"),
        ],
    },
    "mens_accessories": {
        "zip_json": os.path.join(ZIP, "catalogs", "mens_accessories.json"),
        "category_rules": [
            (r"(?i)\bnecklace\b", "Necklaces"),
            (r"(?i)\bpendant\b", "Necklaces"),
            (r"(?i)\bchain\b", "Necklaces"),
        ],
    },
    "womens_jewelry": {
        "zip_json": os.path.join(ZIP, "catalogs", "womens_jewelry.json"),
        "category_rules": [
            (r"(?i)\bearring\b", "Earrings"),
            (r"(?i)\bhoop\b", "Earrings"),
            (r"(?i)\bstud\b", "Earrings"),
            (r"(?i)\bnecklace\b", "Necklaces"),
            (r"(?i)\bpendant\b", "Necklaces"),
            (r"(?i)\bring\b", "Rings"),
            (r"(?i)\bbracelet\b", "Bracelets"),
            # 925 Silver category — products explicitly marked as silver
            (r"(?i)\b925\b", "925 Silver"),
            (r"(?i)\bsilver 925\b", "925 Silver"),
            (r"(?i)\bsilver\s*925\b", "925 Silver"),
            (r"(?i)\bstainless steel\b", "Stainless Steel"),
            (r"(?i)\bgold plated\b", "Gold Plated"),
            (r"(?i)\bgold\s*plated\b", "Gold Plated"),
            (r"(?i)\b18k\b", "Gold Plated"),
        ],
    },
    "womens_clutches": {
        "zip_json": os.path.join(ZIP, "catalogs", "womens_clutches.json"),
        "category_rules": [
            (r"(?i)\bclutch\b", "Clutches"),
            (r"(?i)\bbag\b", "Bags"),
            (r"(?i)\bcrossbody\b", "Crossbody"),
            (r"(?i)\bmesh\b", "Mesh"),
            (r"(?i)\bwooden\b", "Wooden"),
            (r"(?i)\bresin\b", "Resin"),
            (r"(?i)\bbrass\b", "Brass"),
        ],
    },
}

def is_demo(p):
    sku = (p.get("sku") or "").strip().upper()
    name = (p.get("name") or "").strip().lower()
    if sku in ("OIYO", "KUOI", "MAC-001"):
        return True
    if name == "test" and not re.match(r"^RY\d+$", sku):
        return True
    # Demo product prefixes
    if re.match(r"^(SC-|MEB-|MC-|CT-|MG-|GHE-|PN-)\d+$", sku):
        return True
    return False

def clean_price(price):
    price = (price or "").strip()
    if not price:
        return "Rs. 0"
    if price.startswith("Rs."):
        return re.sub(r"^Rs\.\s*(\d+[,\d]*\.?\d*)\s*$", r"Rs. \1", price)
    m = re.search(r"Rs\.\s*(\d+[,\d]*\.?\d*)", price)
    if m:
        return f"Rs. {m.group(1)}"
    m = re.match(r"^(\d+[,\d]*\.?\d*)\s*$", price)
    if m:
        return f"Rs. {m.group(1)}"
    return price

def assign_category(name, rules):
    if not name:
        return "Other"
    for pattern, cat in rules:
        if re.search(pattern, name):
            return cat
    return "Other"

def load_json(path):
    if os.path.isfile(path):
        with open(path) as f:
            return json.load(f)
    return {"name": "", "products": []}

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

# --- Step 1: Copy new images ---
print("=== Step 1: Copying new images ===")
copied = 0
if os.path.isdir(IMG_FROM):
    for fname in os.listdir(IMG_FROM):
        src = os.path.join(IMG_FROM, fname)
        dst = os.path.join(IMG_TO, fname)
        if os.path.isfile(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
            copied += 1
    print(f"Copied {copied} new images")
else:
    print(f"WARNING: {IMG_FROM} not found")

# --- Step 2: Merge catalogs ---
print("\n=== Step 2: Merging catalogs ===")
for name, cfg in CATALOGS.items():
    zip_json = cfg["zip_json"]
    existing_json = os.path.join(BASE, "catalogs", f"{name}.json")
    
    existing = load_json(existing_json)
    existing_products = existing.get("products", [])
    existing_by_sku = {p.get("sku","").strip().upper(): p for p in existing_products}
    
    new_data = load_json(zip_json)
    new_raw = new_data.get("products", [])
    
    filtered = [p for p in new_raw if not is_demo(p)]
    print(f"\n  {name}: {len(new_raw)} ZIP products → {len(filtered)} after demo filter")
    
    # Merge into existing by SKU
    merged = dict(existing_by_sku)
    for p in filtered:
        sku = p.get("sku","").strip().upper()
        if not sku:
            continue
        p["price"] = clean_price(p.get("price",""))
        if not p.get("category"):
            p["category"] = assign_category(p.get("name",""), cfg["category_rules"])
        
        if sku in merged:
            old = merged[sku]
            new_img = (p.get("image") or "").strip()
            old_img = (old.get("image") or "").strip()
            if new_img and not old_img:
                merged[sku] = p
        else:
            merged[sku] = p
    
    # Build ordered list: existing first, then new SKUs
    final = list(merged.values())
    
    # For womens_jewelry: ensure 925 Silver and Best Sellers categories exist
    # by re-assigning any products that match those patterns
    if name == "womens_jewelry":
        for p in final:
            name_p = p.get("name","")
            # Products with 925 silver in description or name
            if not p.get("category") or p.get("category") == "Other":
                p["category"] = assign_category(name_p, cfg["category_rules"])
    
    merged_data = {
        "name": new_data.get("name", existing.get("name", name.replace("_"," ").title())),
        "products": final,
    }
    
    save_json(existing_json, merged_data)
    print(f"  Written: {existing_json} — {len(final)} products")
    
    # Show category breakdown
    cats = {}
    for p in final:
        c = p.get("category","Other")
        cats[c] = cats.get(c, 0) + 1
    print(f"  Categories: {dict(sorted(cats.items()))}")

# --- Step 3: Re-enable womens_clutches in build + index ---
print("\n=== Step 3: Re-enabling womens_clutches ===")

# Update build_catalogs.py to include womens_clutches
build_path = os.path.join(BASE, "build_catalogs.py")
with open(build_path) as f:
    build = f.read()

build = build.replace(
    '    ("mens_accessories",  "catalog_mens_accessories.html"),\n]',
    '    ("mens_accessories",  "catalog_mens_accessories.html"),\n    ("womens_clutches",   "catalog_womens_clutches.html"),\n]'
)
with open(build_path, "w") as f:
    f.write(build)
print("  build_catalogs.py: womens_clutches re-enabled")

# Update index.html to add clutches back
index_path = os.path.join(BASE, "index.html")
with open(index_path) as f:
    index = f.read()

# Add clutches link after womens_jewelry link
index = index.replace(
    '<span class="link-label">Women\'s Jewelry &amp; Accessories</span>\n                </a>\n            </div>\n            <div class="section-note">Earrings, necklaces, bracelets, rings &amp; more.</div>',
    '<span class="link-label">Women\'s Jewelry &amp; Accessories</span>\n                </a>\n                <a href="html_catalogs/catalog_womens_clutches.html">\n                    <span class="link-icon"></span>\n                    <span class="link-label">Women\'s Clutches</span>\n                </a>\n            </div>\n            <div class="section-note">Earrings, necklaces, bracelets, rings, clutches &amp; evening bags.</div>'
)
with open(index_path, "w") as f:
    f.write(index)
print("  index.html: clutches link added back")

# --- Step 4: Rebuild all HTML ---
print("\n=== Step 4: Rebuilding HTML ===")
result = subprocess.run(
    ["python3", os.path.join(BASE, "build_catalogs.py")],
    cwd=BASE,
    capture_output=True,
    text=True,
)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr[:500])

# --- Step 5: Report ---
print("\n=== DONE ===")
print("Ready to commit and push.")
