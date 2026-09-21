#!/usr/bin/env python3
"""Fix category assignments for womens_jewelry after merge."""

import json, re, os

BASE = "/Users/syedabdullah.hashmi/Desktop/html catalogger"

def assign_category(text, rules):
    if not text:
        return "Other"
    for pattern, cat in rules:
        if re.search(pattern, text):
            return cat
    return "Other"

path = os.path.join(BASE, "catalogs", "womens_jewelry.json")
with open(path) as f:
    data = json.load(f)

rules = [
    (r"(?i)\b925\b", "925 Silver"),
    (r"(?i)\bsilver\s*925\b", "925 Silver"),
    (r"(?i)\bbestseller\b", "Best Sellers"),
    (r"(?i)\bgold\s*plated\b", "Gold Plated"),
    (r"(?i)\b18k\s*gold\s*plated\b", "Gold Plated"),
    (r"(?i)\bstainless\s*steel\b", "Stainless Steel"),
    (r"(?i)\bearring\b", "Earrings"),
    (r"(?i)\bhoop\b", "Earrings"),
    (r"(?i)\bstud\b", "Earrings"),
    (r"(?i)\bnecklace\b", "Necklaces"),
    (r"(?i)\bpendant\b", "Necklaces"),
    (r"(?i)\bring\b", "Rings"),
    (r"(?i)\bbracelet\b", "Bracelets"),
]

for p in data["products"]:
    name = (p.get("name") or "").strip()
    desc = (p.get("description") or "").strip()
    combined = f"{name} {desc}"
    if not p.get("category") or p.get("category") == "Other":
        new_cat = assign_category(combined, rules)
        if new_cat != "Other":
            p["category"] = new_cat

with open(path, "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")

cats = {}
for p in data["products"]:
    c = p.get("category","?")
    cats[c] = cats.get(c,0) + 1
print("womens_jewelry categories after fix:")
for c,n in sorted(cats.items()):
    print(f"  {c}: {n}")

for cat_name in ["925 Silver", "Best Sellers", "Gold Plated", "Stainless Steel"]:
    print(f"\n{cat_name}:")
    for p in data["products"]:
        if p.get("category") == cat_name:
            print(f"  {p['sku']:8} | {p['name'][:55]:55} | {p.get('description','')[:40]}")
