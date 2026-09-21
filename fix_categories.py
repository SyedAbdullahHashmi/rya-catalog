#!/usr/bin/env python3
"""
1. womens_jewelry: move Best Sellers category → Earrings, keep best_seller tag
2. mens_jewelry: merge mens_accessories products, tag best_seller
3. Unflag OOS from earrings that got over-flagged
4. Remove mens_accessories from build/index
"""

import json

BASE = "/Users/syedabdullah.hashmi/Desktop/html catalogger"

# ---- 1. womens_jewelry: Best Sellers → Earrings ----
wj = json.load(open(f"{BASE}/catalogs/womens_jewelry.json"))
moved = 0
for p in wj["products"]:
    if p.get("category") == "Best Sellers":
        p["category"] = "Earrings"
        moved += 1
        # Ensure best_seller tag exists (it should already)
        tags = p.get("tags") or []
        if "best_seller" not in tags:
            tags.append("best_seller")
            p["tags"] = tags
json.dump(wj, open(f"{BASE}/catalogs/womens_jewelry.json", "w"), indent=2, ensure_ascii=False)
print(f"womens_jewelry: moved {moved} products from Best Sellers → Earrings")

# ---- 2. Unflag OOS from earrings that shouldn't be OOS ----
# The earlier script flagged all earrings OOS. Only keep OOS for products
# that are genuinely out of stock. For now, unflag all earrings OOS
# (user can re-flag via admin). Keep best_seller tag.
oos_removed = 0
for p in wj["products"]:
    if p.get("category") == "Earrings":
        tags = p.get("tags") or []
        if "out_of_stock" in tags:
            tags.remove("out_of_stock")
            p["tags"] = tags
            oos_removed += 1
json.dump(wj, open(f"{BASE}/catalogs/womens_jewelry.json", "w"), indent=2, ensure_ascii=False)
print(f"womens_jewelry: removed OOS from {oos_removed} earrings")

# ---- 3. mens_jewelry: merge mens_accessories + tag best_seller ----
mj = json.load(open(f"{BASE}/catalogs/mens_jewelry.json"))
existing_skus = {p["sku"] for p in mj["products"]}

ma = json.load(open(f"{BASE}/catalogs/mens_accessories.json"))
added = 0
for p in ma["products"]:
    if p["sku"] not in existing_skus:
        p["category"] = "Necklaces"  # pendant necklaces
        p["tags"] = ["best_seller"]
        mj["products"].append(p)
        added += 1
    else:
        # Already exists — just ensure best_seller tag
        existing = next(p2 for p2 in mj["products"] if p2["sku"] == p["sku"])
        tags = existing.get("tags") or []
        if "best_seller" not in tags:
            tags.append("best_seller")
            existing["tags"] = tags

json.dump(mj, open(f"{BASE}/catalogs/mens_jewelry.json", "w"), indent=2, ensure_ascii=False)
print(f"mens_jewelry: added {added} products from mens_accessories")

# ---- 4. Remove mens_accessories from build + index ----
import os

# build_catalogs.py: remove mens_accessories from CATALOG_FILES
bc = open(f"{BASE}/build_catalogs.py").read()
bc = bc.replace('"mens_accessories.json",\n        ', '')
bc = bc.replace('"mens_accessories.json"\n    ]', '"mens_accessories.json"\n    ]')  # no-op if already gone
# More robust: find and remove the line
lines = bc.split('\n')
new_lines = []
for line in lines:
    if '"mens_accessories.json"' in line and 'CATALOG_FILES' in ''.join(lines[max(0,lines.index(line)-3):lines.index(line)]):
        continue
    new_lines.append(line)
# Simpler approach: just remove the specific line
bc2 = '\n'.join(new_lines)
if bc2 != bc:
    bc = bc2
elif '"mens_accessories.json"' in bc:
    # Remove any line containing mens_accessories.json in CATALOG_FILES context
    bc = '\n'.join(l for l in bc.split('\n') if 'mens_accessories.json' not in l)
open(f"{BASE}/build_catalogs.py", "w").write(bc)
print("Removed mens_accessories from build_catalogs.py")

# index.html: remove mens_accessories link
idx = open(f"{BASE}/index.html").read()
import re
# Remove the mens accessories / best sellers link block
idx = re.sub(
    r'<div class="catalog-card">\s*<a href="catalog_mens_accessories\.html">\s*<div class="cat-icon"><svg[^>]*>.*?</svg></div>\s*<div class="cat-label">.*?Men.s Best Sellers.*?</div>\s*</a>\s*</div>',
    '', idx, flags=re.DOTALL)
# Also try simpler pattern
idx = re.sub(
    r'<a href="catalog_mens_accessories\.html">[^<]*Men.s Best Sellers[^<]*</a>',
    '', idx)
open(f"{BASE}/index.html", "w").write(idx)
print("Removed mens_accessories link from index.html")

# Verify
print("\n=== Verification ===")
wj2 = json.load(open(f"{BASE}/catalogs/womens_jewelry.json"))
print(f"womens_jewelry: {len(wj2['products'])} products")
cats = {}
for p in wj2['products']:
    c = p.get('category','?')
    cats[c] = cats.get(c,0)+1
for c,n in sorted(cats.items()):
    print(f"  {c}: {n}")
print(f"  Best Sellers category remaining: {sum(1 for p in wj2['products'] if p.get('category')=='Best Sellers')}")

mj2 = json.load(open(f"{BASE}/catalogs/mens_jewelry.json"))
print(f"\nmens_jewelry: {len(mj2['products'])} products")
bs = [p['sku'] for p in mj2['products'] if 'best_seller' in (p.get('tags') or [])]
print(f"  best_seller tagged: {len(bs)} — {bs}")
oos = [p['sku'] for p in mj2['products'] if 'out_of_stock' in (p.get('tags') or [])]
print(f"  out_of_stock tagged: {len(oos)} — {oos}")

# Check mens_accessories still exists on disk (hidden, not in build)
print(f"\nmens_accessories.json still on disk: {os.path.exists(f'{BASE}/catalogs/mens_accessories.json')}")
print(f"In build_catalogs CATALOG_FILES: {'mens_accessories' in bc}")
print(f"In index.html: {'mens_accessories' in open(f'{BASE}/index.html').read()}")
