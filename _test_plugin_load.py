#!/usr/bin/env python3
"""Quick test: can Hermes' plugin loader discover and register the catalog_tool plugin?"""
import sys, json
sys.path.insert(0, "/Users/syedabdullah.hashmi/.hermes/hermes-agent")

from hermes_cli.plugins import discover_plugins, get_plugin_toolsets, get_plugin_manager

# Force discovery
discover_plugins(force=True)
mgr = get_plugin_manager()

print("=== Discovered plugins ===")
for p in mgr.list_plugins():
    print(f"  {p['name']} ({p['source']}): enabled={p['enabled']}, tools={p['tools']}, error={p['error']}")

print()
print("=== Plugin toolsets ===")
for ts_key, label, desc in get_plugin_toolsets():
    print(f"  {ts_key}: {label} — {desc}")

print()
# Try to dispatch a tool
from tools.registry import registry
for name in ("catalog_help", "catalog_list_catalogs"):
    entry = registry.get_entry(name)
    if entry:
        print(f"=== {name} (found in registry) ===")
        result = registry.dispatch(name, {})
        print(result[:200])
    else:
        print(f"=== {name}: NOT FOUND in registry ===")
