#!/usr/bin/env python3
"""Quick end-to-end test of the catalog plugin — simulates what Hermes does."""
import json
import sys
import types

HERMES_HOME = "/Users/syedabdullah.hashmi/.hermes"
sys.path.insert(0, f"{HERMES_HOME}/hermes-agent")

# Minimal mock of what Hermes passes to register()
class FakeRegistry:
    def __init__(self):
        self.tools = {}
    def register(self, name, toolset, schema, handler, check_fn):
        self.tools[name] = {"toolset": toolset, "handler": handler, "schema": schema}

class FakeContext:
    def __init__(self, registry):
        self._registry = registry
    def register_tool(self, **kw):
        self._registry.register(**kw)

# Load plugin manifest + module
import importlib.util, os
plugin_dir = f"{HERMES_HOME}/plugins/catalog_tool"
spec = importlib.util.spec_from_file_location("catalog_tool", f"{plugin_dir}/tool.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

registry = FakeRegistry()
ctx = FakeContext(registry)
mod.register(ctx)

print(f"Registered {len(registry.tools)} tools: {sorted(registry.tools.keys())}")
print()

# Test 1: catalog_help
print("=== catalog_help ===")
r = json.loads(registry.tools["catalog_help"]["handler"]("{}"))
print(r["help"])
print()

# Test 2: catalog_list_catalogs
print("=== catalog_list_catalogs ===")
r = json.loads(registry.tools["catalog_list_catalogs"]["handler"]("{}"))
for c in r["catalogs"]:
    print(f"  {c['key']}: {c['name']} — {c['product_count']} products, cats: {c['categories']}")
print()

# Test 3: catalog_list_categories (mens_jewelry)
print("=== catalog_list_categories (mens_jewelry) ===")
r = json.loads(registry.tools["catalog_list_categories"]["handler"]('{"catalog":"mens_jewelry"}'))
for c in r["categories"]:
    print(f"  {c['category']}: {c['count']}")
print()

# Test 4: catalog_list_products (mens_jewelry, first 3)
print("=== catalog_list_products (mens_jewelry, limit 3) ===")
r = json.loads(registry.tools["catalog_list_products"]["handler"]('{"catalog":"mens_jewelry","limit":3}'))
for p in r["products"]:
    print(f"  [{p['category']}] {p['name']} — {p['price']} (SKU: {p['sku']})")
print(f"  ... ({r['count']} shown of {r['count']} total)")
print()

# Test 5: catalog_add_product (add a test product)
print("=== catalog_add_product (TEST) ===")
test_payload = json.dumps({
    "catalog": "mens_accessories",
    "name": "Hermes Test Watch",
    "sku": "HERMES-TEST-001",
    "description": "A test product added by the plugin end-to-end test.",
    "price": "Rs. 999",
    "category": "Watches",
})
r = json.loads(registry.tools["catalog_add_product"]["handler"](test_payload))
print(json.dumps(r, indent=2))
print()

# Verify it landed in the JSON
with open(f"{HERMES_HOME}/../../Desktop/html catalogger/catalogs/mens_accessories.json") as f:
    data = json.load(f)
added = [p for p in data["products"] if p.get("sku") == "HERMES-TEST-001"]
if added:
    print(f"VERIFIED: product found in mens_accessories.json — {added[0]['name']}")
else:
    print("ERROR: product NOT found in JSON after add!")

# Cleanup: remove the test product
data["products"] = [p for p in data["products"] if p.get("sku") != "HERMES-TEST-001"]
with open(f"{HERMES_HOME}/../../Desktop/html catalogger/catalogs/mens_accessories.json", "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")
print("Cleaned up test product.")
