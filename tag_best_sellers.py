#!/usr/bin/env python3
"""Add best_seller tags to products that aren't tagged yet + tag OOS products."""

import json, glob

BASE = "/Users/syedabdullah.hashmi/Desktop/html catalogger"

# OOS products (from earlier output) — mark them
oos_skus = {
    "mens_jewelry":   ["RY381", "RY456", "RY459", "RY461", "RY462", "RY463", "RY464", "RY466",
                       "RY467", "RY359", "RY455", "RY356", "RY447", "RY448", "RY452", "RY460",
                       "RY445", "RY446"],
    "womens_jewelry": ["RY471", "RY475", "RY473", "RY469", "RY373", "RY410", "RY412",
                       "RY408", "RY407", "RY406", "RY375", "RY377", "RY378", "RY374",
                       "RY486", "RY485", "RY484", "RY483", "RY482", "RY481", "RY480",
                       "RY479"],
}

for catalog_key, skus in oos_skus.items():
    path = f"{BASE}/catalogs/{catalog_key}.json"
    with open(path) as f:
        d = json.load(f)
    changed = 0
    for p in d["products"]:
        if p["sku"] in skus:
            tags = p.get("tags") or []
            if "out_of_stock" not in tags:
                tags.append("out_of_stock")
                p["tags"] = tags
                changed += 1
    if changed:
        with open(path, "w") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"  {catalog_key}: tagged {changed} products OOS")

print("OOS tags added.")

# Best-seller candidates — add best_seller tag
# Only for products NOT already in "Best Sellers" category
mens_brs = {"RY467","RY466","RY464","RY452","RY445","RY356"}

for catalog_key in ["mens_jewelry", "womens_jewelry"]:
    path = f"{BASE}/catalogs/{catalog_key}.json"
    with open(path) as f:
        d = json.load(f)
    changed = 0
    for p in d["products"]:
        name = p["name"].lower()
        cat = p.get("category", "")
        # Skip if already in Best Sellers category
        if cat == "Best Sellers":
            continue
        # Determine if best seller
        is_bs = False
        if catalog_key == "mens_jewelry":
            is_bs = (p["sku"] in mens_brs or
                     "statement ring" in name or
                     "hoop earring" in name or
                     "cuban" in name or "chain" in name or
                     "tennis bracelet" in name)
        else:  # womens
            is_bs = ("hoop" in name or "stud" in name or "drop" in name or
                     "crystal" in name or "pearl" in name or
                     "geometric" in name or "leaf" in name or
                     "heart hoop" in name)
        if is_bs:
            tags = p.get("tags") or []
            if "best_seller" not in tags:
                tags.append("best_seller")
                p["tags"] = tags
                changed += 1
    if changed:
        with open(path, "w") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"  {catalog_key}: added best_seller tag to {changed} products")

print("Done.")
