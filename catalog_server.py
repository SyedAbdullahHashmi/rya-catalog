#!/usr/bin/env python3
"""Catalog Manager — local form server.
Serves the add-product form at / and accepts POST /add to append products to one of 4 catalog JSON files.

Black / gray / white UI. Supports either an image URL or a locally-picked file (uploaded as a data URL, stored in catalog_images/)."""

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CATA_DIR = os.path.join(BASE_DIR, "catalogs")
IMG_DIR = os.path.join(BASE_DIR, "images")
FORM_PATH = os.path.join(BASE_DIR, "catalog_form.html")

CATALOGS = {
    "mens_jewelry":      os.path.join(CATA_DIR, "mens_jewelry.json"),
    "womens_jewelry":    os.path.join(CATA_DIR, "womens_jewelry.json"),
    "womens_clutches":   os.path.join(CATA_DIR, "womens_clutches.json"),
    "mens_accessories":  os.path.join(CATA_DIR, "mens_accessories.json"),
}


def read_catalog(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_catalog(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _auto_publish(catalog_key):
    """Rebuild HTML catalogs, commit, and push to GitHub after a product is added."""
    # 1. Rebuild HTML
    script = Path(BASE_DIR) / "build_catalogs.py"
    subprocess.run([sys.executable, str(script)], cwd=BASE_DIR,
                   capture_output=True, timeout=120)

    # 2. Git add + commit + push
    catalog_file = Path(CATALOGS[catalog_key])
    html_dir = Path(BASE_DIR) / "html_catalogs"
    files_to_add = [str(catalog_file)]
    if html_dir.exists():
        files_to_add.extend(str(p) for p in html_dir.glob("catalog_*.html"))

    subprocess.run(["git", "add", "."], cwd=BASE_DIR,
                   capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", f"Add product to {catalog_key}"],
                   cwd=BASE_DIR, capture_output=True, check=False)
    subprocess.run(["git", "push", "origin", "main"],
                   cwd=BASE_DIR, capture_output=True, check=False)


def save_uploaded_image(data_url):
    """Store a data URL image into images/<uuid>.<ext>. Return relative path like images/abc123.jpg."""
    if not data_url or not data_url.startswith("data:"):
        return None
    header, encoded = data_url.split(",", 1)
    mime = header.split(";")[0].replace("data:", "")
    ext_map = {"image/jpeg": "jpg", "image/jpg": "jpg", "image/png": "png",
               "image/webp": "webp", "image/gif": "gif", "image/bmp": "bmp"}
    ext = ext_map.get(mime, "png")
    raw = __import__("base64").b64decode(encoded)
    fname = f"{uuid.uuid4().hex}.{ext}"
    os.makedirs(IMG_DIR, exist_ok=True)
    path = os.path.join(IMG_DIR, fname)
    with open(path, "wb") as f:
        f.write(raw)
    rel = os.path.relpath(path, BASE_DIR).replace("\\", "/")
    return rel


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._serve_form()
        elif self.path == "/catalog_form.html":
            self._serve_form()
        elif self.path.startswith("/catalog_") and self.path.endswith(".html"):
            # Catalog HTML files live in html_catalogs/
            rel = os.path.join("html_catalogs", self.path.lstrip("/"))
            full = os.path.join(BASE_DIR, rel)
            if os.path.isfile(full):
                self._serve_file(full)
            else:
                self.send_error(404)
        else:
            # Serve static files (images, etc.) relative to BASE_DIR
            rel = self.path.lstrip("/")
            full = os.path.join(BASE_DIR, rel)
            if os.path.isfile(full):
                self._serve_file(full)
            else:
                self.send_error(404)

    def do_POST(self):
        if self.path != "/add":
            self.send_error(404)
            return
        try:
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        except Exception:
            self.send_json({"error": "Invalid JSON"}, 400)
            return

        catalog_key = (data.get("catalog") or "").strip()
        if catalog_key not in CATALOGS:
            self.send_json({"error": "Unknown catalog. Pick one of the four."}, 400)
            return

        name = (data.get("name") or "").strip()
        sku = (data.get("sku") or "").strip()
        description = (data.get("description") or "").strip()
        price = (data.get("price") or "").strip()
        image_url = (data.get("image_url") or "").strip()
        image_data = (data.get("image_data") or "").strip()
        category = (data.get("category") or "Other").strip() or "Other"

        if not name or not sku or not description or not price:
            self.send_json({"error": "name, sku, description, and price are required."}, 400)
            return

        # Resolve image: uploaded file takes precedence, then URL, then none
        image = ""
        image_verb = ""
        if image_data:
            rel = save_uploaded_image(image_data)
            if rel:
                image = rel
                image_verb = "image uploaded"
        elif image_url:
            image = image_url
            image_verb = "URL used"

        cat = read_catalog(CATALOGS[catalog_key])
        cat["products"].append({
            "name": name,
            "sku": sku,
            "description": description,
            "price": price,
            "image": image,
            "category": category,
        })
        write_catalog(CATALOGS[catalog_key], cat)

        # Auto-publish: rebuild HTML + commit + push to GitHub
        try:
            _auto_publish(catalog_key)
        except Exception as e:
            # Log but don't fail the request — product is saved either way
            sys.stderr.write(f"auto-publish failed: {e}\n")

        self.send_json({
            "ok": True,
            "name": name,
            "sku": sku,
            "count": len(cat["products"]),
            "catalog": cat["name"],
            "image_verb": image_verb,
        })

    def _serve_form(self):
        with open(FORM_PATH, "rb") as f:
            html = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html)

    def _serve_file(self, full_path):
        ct = "application/octet-stream"
        if full_path.endswith(".html"):
            ct = "text/html; charset=utf-8"
        elif full_path.endswith(".css"):
            ct = "text/css"
        elif full_path.endswith(".js"):
            ct = "application/javascript"
        elif full_path.endswith(".png"):
            ct = "image/png"
        elif full_path.endswith(".jpg") or full_path.endswith(".jpeg"):
            ct = "image/jpeg"
        elif full_path.endswith(".gif"):
            ct = "image/gif"
        elif full_path.endswith(".webp"):
            ct = "image/webp"
        with open(full_path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", len(data))
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, obj, status=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # quiet


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5001
    server = HTTPServer(("127.0.0.1", port), Handler)
    print(f"Catalog Manager running: http://127.0.0.1:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
