"""Dependency-free WSGI application, served by Gunicorn in production.

No local product storage, Git subprocesses, or credentials in browser code.
"""
import base64
from collections import OrderedDict
import hashlib
import hmac
from http.cookies import SimpleCookie
import json
import logging
import os
from pathlib import Path
import re
import secrets
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlsplit
from urllib.request import Request, urlopen

CATALOGS = {
    "mens_jewelry": "Men’s jewellery & accessories",
    "womens_jewelry": "Women’s jewellery & accessories",
    "womens_clutches": "Women’s clutches",
}
ROOT = Path(__file__).parent
MAX_BODY = 12 * 1024 * 1024
MAX_IMAGE = 8 * 1024 * 1024


class Problem(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600000)
    return "pbkdf2_sha256$600000$" + salt + "$" + digest.hex()


def password_matches(password, encoded):
    try:
        algorithm, rounds, salt, expected = encoded.split("$")
        if algorithm != "pbkdf2_sha256" or int(rounds) != 600000:
            return False
        return hmac.compare_digest(password_hash(password, salt), encoded)
    except (ValueError, TypeError):
        return False


class GitHub:
    def __init__(self, repository, token, branch="main"):
        if not re.fullmatch(r"[\w.-]+/[\w.-]+", repository):
            raise ValueError("Invalid GITHUB_REPOSITORY")
        self.repository, self.token, self.branch = repository, token, branch
        self.base = "https://api.github.com/repos/" + repository

    def call(self, method, path, data=None):
        headers = {"Authorization": "Bearer " + self.token,
                   "Accept": "application/vnd.github+json",
                   "X-GitHub-Api-Version": "2022-11-28",
                   "User-Agent": "Ryra-Catalog-Admin"}
        body = None if data is None else json.dumps(data).encode()
        if body is not None:
            headers["Content-Type"] = "application/json"
        req = Request(self.base + path, data=body, headers=headers, method=method)
        try:
            with urlopen(req, timeout=30) as response:
                return json.load(response)
        except HTTPError as exc:
            if exc.code in (409, 422):
                raise Problem("The catalog changed while you were saving. Reload and try again.", 409) from None
            if exc.code in (401, 403):
                raise Problem("GitHub access needs the owner’s attention. Your change was not confirmed.", 502) from None
            raise Problem("GitHub could not complete this request. Please try again shortly.", 502) from None
        except (URLError, TimeoutError, OSError):
            raise Problem("GitHub could not be reached. The result is unconfirmed; use Check publishing, then reload before retrying.", 502) from None

    def snapshot(self, key):
        head = self.call("GET", "/git/ref/heads/" + quote(self.branch, safe=""))["object"]["sha"]
        path = "/contents/catalogs/" + key + ".json?ref=" + head
        content = self.call("GET", path)
        catalog = json.loads(base64.b64decode(content["content"]))
        if not isinstance(catalog, dict) or not isinstance(catalog.get("products"), list):
            raise Problem("This catalog has an unsupported format. Contact the owner.", 502)
        return head, content["sha"], catalog

    def commit(self, key, head, catalog, assets, message):
        # Publish JSON and image together, or neither. Never force-push.
        entries = [{"path": "catalogs/" + key + ".json", "mode": "100644", "type": "blob",
                    "content": json.dumps(catalog, ensure_ascii=False, indent=2) + "\n"}]
        for path, data in assets.items():
            blob = self.call("POST", "/git/blobs", {
                "content": base64.b64encode(data).decode(), "encoding": "base64"})
            entries.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        parent = self.call("GET", "/git/commits/" + head)
        tree = self.call("POST", "/git/trees", {"base_tree": parent["tree"]["sha"], "tree": entries})
        commit = self.call("POST", "/git/commits", {
            "message": message, "tree": tree["sha"], "parents": [head]})
        self.call("PATCH", "/git/refs/heads/" + quote(self.branch, safe=""), {
            "sha": commit["sha"], "force": False})
        return commit["sha"]

    def status(self, sha):
        query = "?per_page=10&branch=" + quote(self.branch, safe="")
        if sha:
            query += "&head_sha=" + sha
        runs = self.call("GET", "/actions/workflows/pages.yml/runs" + query).get("workflow_runs", [])
        if not runs:
            return {"state": "waiting", "message": "Waiting for GitHub to start the catalog build."}
        run = runs[0]
        if run["status"] != "completed":
            state, message = "building", "GitHub is rebuilding and publishing the catalog."
        elif run.get("conclusion") == "success":
            state, message = "live", "The catalog deployment completed successfully."
        else:
            state, message = "failed", "The update is saved in GitHub, but deployment did not succeed. Contact the owner."
        return {"state": state, "message": message, "url": run["html_url"], "commit": run["head_sha"]}


def read_image(value):
    if not isinstance(value, str):
        raise Problem("Choose a valid image.")
    match = re.fullmatch(r"data:image/(png|jpeg|jpg|webp|gif);base64,([A-Za-z0-9+/=\s]+)", value)
    if not match:
        raise Problem("Use a PNG, JPG, WebP or GIF image.")
    try:
        data = base64.b64decode(match[2], validate=False)
    except ValueError:
        raise Problem("This image could not be read.") from None
    if len(data) > MAX_IMAGE:
        raise Problem("Choose an image smaller than 8 MB.", 413)
    kind = match[1].replace("jpeg", "jpg")
    valid = {"png": data.startswith(b"\x89PNG\r\n\x1a\n"),
             "jpg": data.startswith(b"\xff\xd8\xff"),
             "gif": data.startswith((b"GIF87a", b"GIF89a")),
             "webp": data[:4] == b"RIFF" and data[8:12] == b"WEBP"}
    if not valid[kind]:
        raise Problem("The selected file does not match its image type.")
    return "images/hosted_" + hashlib.sha256(data).hexdigest() + "." + kind, data


def product_fields(data):
    fields = {}
    for key, limit in [("name", 200), ("sku", 100), ("description", 5000), ("category", 100)]:
        value = data.get(key, "")
        if not isinstance(value, str) or len(value.strip()) > limit:
            raise Problem("Check the " + key + " field.")
        fields[key] = value.strip()
    if not all(fields[k] for k in ("name", "sku", "description", "category")):
        raise Problem("Name, SKU, description and category are required.")
    price = str(data.get("price", "")).strip()
    price = re.sub(r"^(?:Rs\.\s*|Rs\s+|INR\s+|₹\s*)", "", price, flags=re.I).replace(",", "")
    if not re.fullmatch(r"\d{1,8}(?:\.\d{1,2})?", price):
        raise Problem("Enter a numeric price in rupees, for example 1999.")
    fields["price"] = "Rs. " + price
    for key in ("out_of_stock", "best_seller"):
        if key in data and not isinstance(data[key], bool):
            raise Problem("Invalid product flag.")
        fields[key] = data.get(key, False)
    return fields


class CatalogApp:
    def __init__(self, env=None, github=None):
        env = os.environ if env is None else env
        self.secret = env.get("SESSION_SECRET", "")
        if len(self.secret) < 32:
            raise ValueError("Set SESSION_SECRET to at least 32 random characters")
        self.accounts = json.loads(env.get("STAFF_ACCOUNTS_JSON", "{}"))
        email, password = env.get("ADMIN_EMAIL", "").strip().lower(), env.get("ADMIN_PASSWORD", "")
        if email and len(password) >= 14:
            self.accounts[email] = password_hash(password)
        if not self.accounts or any(not isinstance(v, str) or not v.startswith("pbkdf2_sha256$600000$") for v in self.accounts.values()):
            raise ValueError("Configure ADMIN_EMAIL and ADMIN_PASSWORD (14+ characters), or valid STAFF_ACCOUNTS_JSON")
        self.accounts = {k.strip().lower(): v for k, v in self.accounts.items()}
        self.dummy_hash = password_hash(secrets.token_urlsafe(24))
        self.secure = env.get("ALLOW_LOCAL_HTTP") != "1"
        self.github = github or GitHub(env.get("GITHUB_REPOSITORY", "SyedAbdullahHashmi/rya-catalog"),
                                      env.get("GITHUB_TOKEN", ""), env.get("GITHUB_BRANCH", "main"))
        if github is None and not self.github.token:
            raise ValueError("Set GITHUB_TOKEN in the hosting environment")
        self.public = "https://syedabdullahhashmi.github.io/rya-catalog/"
        self.attempts, self.lock = OrderedDict(), threading.Lock()

    def seal(self, payload):
        text = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        signature = hmac.new(self.secret.encode(), text.encode(), hashlib.sha256).hexdigest()
        return text + "." + signature

    def session(self, env):
        try:
            cookie = SimpleCookie(env.get("HTTP_COOKIE", ""))["catalog_session"].value
            text, signature = cookie.rsplit(".", 1)
            expected = hmac.new(self.secret.encode(), text.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature, expected):
                return None
            value = json.loads(base64.urlsafe_b64decode(text + "=" * (-len(text) % 4)))
            account = self.accounts.get(value.get("user"), "")
            stamp = hashlib.sha256(account.encode()).hexdigest()
            if value["expires"] < time.time() or not account or value.get("stamp") != stamp:
                return None
            return value
        except (KeyError, ValueError, TypeError):
            return None

    def respond(self, start, status, value, content_type="application/json", extra=()):
        if content_type == "application/json":
            value = json.dumps(value, ensure_ascii=False).encode()
        elif isinstance(value, str):
            value = value.encode()
        names = {200: "OK", 302: "Found", 400: "Bad Request", 401: "Unauthorized", 403: "Forbidden",
                 404: "Not Found", 405: "Method Not Allowed", 409: "Conflict", 413: "Content Too Large",
                 429: "Too Many Requests", 500: "Internal Server Error", 502: "Bad Gateway"}
        headers = [("Content-Type", content_type + ("; charset=utf-8" if content_type.startswith("text/") else "")),
                   ("Content-Length", str(len(value))), ("Cache-Control", "no-store"),
                   ("X-Content-Type-Options", "nosniff"), ("X-Frame-Options", "DENY"),
                   ("Referrer-Policy", "no-referrer"),
                   ("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' https: data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")]
        if self.secure:
            headers.append(("Strict-Transport-Security", "max-age=31536000"))
        start(str(status) + " " + names[status], headers + list(extra))
        return [value]

    def body(self, env):
        try:
            length = int(env.get("CONTENT_LENGTH", "0") or "0")
        except ValueError:
            raise Problem("Invalid request.") from None
        if length < 0 or length > MAX_BODY:
            raise Problem("This upload is too large. Images must be below 8 MB.", 413)
        value = env["wsgi.input"].read(length)
        try:
            if env.get("CONTENT_TYPE", "").split(";")[0] == "application/json":
                parsed = json.loads(value)
                if not isinstance(parsed, dict):
                    raise ValueError()
                return parsed
            return {k: v[0] for k, v in parse_qs(value.decode()).items()}
        except (ValueError, UnicodeError):
            raise Problem("Invalid request data.") from None

    def __call__(self, env, start):
        try:
            return self.route(env, start)
        except Problem as exc:
            return self.respond(start, exc.status, {"error": str(exc)})
        except Exception:
            logging.exception("Catalog admin request failed")
            return self.respond(start, 500, {"error": "The request could not be completed. Reload before trying again."})

    def route(self, env, start):
        path, method = env.get("PATH_INFO", "/"), env.get("REQUEST_METHOD", "GET")
        if path == "/healthz" and method == "GET":
            return self.respond(start, 200, {"ok": True})
        if path in ("/static/app.js", "/static/style.css") and method == "GET":
            file = ROOT / path.lstrip("/")
            return self.respond(start, 200, file.read_bytes(), "text/javascript" if path.endswith(".js") else "text/css")
        if path == "/login" and method == "GET":
            return self.respond(start, 200, (ROOT / "login.html").read_text(), "text/html")
        if path == "/login" and method == "POST":
            # No cross-origin login; SameSite cookie plus CSRF protects authenticated writes.
            origin = env.get("HTTP_ORIGIN")
            if origin and urlsplit(origin).netloc != env.get("HTTP_HOST"):
                raise Problem("Open the sign-in page directly and try again.", 403)
            if env.get("HTTP_SEC_FETCH_SITE") == "cross-site":
                raise Problem("Open the sign-in page directly and try again.", 403)
            data = self.body(env)
            user = str(data.get("email", "")).strip().lower()[:254]
            password = str(data.get("password", ""))
            if len(password) > 1024:
                raise Problem("Invalid email or password.", 401)
            with self.lock:
                now = time.time()
                history = [t for t in self.attempts.pop(user, []) if t > now - 900]
                self.attempts[user] = history + [now]
                while len(self.attempts) > 2000:
                    self.attempts.popitem(last=False)
                if len(history) >= 5:
                    raise Problem("Too many sign-in attempts. Try again in 15 minutes.", 429)
            stored = self.accounts.get(user, self.dummy_hash)
            if not password_matches(password, stored) or user not in self.accounts:
                raise Problem("Invalid email or password.", 401)
            payload = {"user": user, "expires": int(time.time()) + 8 * 3600,
                       "csrf": secrets.token_urlsafe(32), "stamp": hashlib.sha256(stored.encode()).hexdigest()}
            cookie = "catalog_session=" + self.seal(payload) + "; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800"
            if self.secure:
                cookie += "; Secure"
            with self.lock:
                self.attempts.pop(user, None)
            return self.respond(start, 200, {"ok": True}, extra=[("Set-Cookie", cookie)])
        session = self.session(env)
        if not session:
            if path == "/" and method == "GET":
                return self.respond(start, 302, "", "text/plain", [("Location", "/login")])
            raise Problem("Please sign in again.", 401)
        if method not in ("GET", "POST"):
            raise Problem("Method not allowed.", 405)
        if method == "POST":
            if not hmac.compare_digest(env.get("HTTP_X_CSRF_TOKEN", ""), session["csrf"]):
                raise Problem("Your session needs refreshing. Reload this page.", 403)
        if path == "/" and method == "GET":
            return self.respond(start, 200, (ROOT / "index.html").read_text(), "text/html")
        if path == "/api/session" and method == "GET":
            return self.respond(start, 200, {"user": session["user"], "csrf": session["csrf"],
                                           "catalogs": CATALOGS, "public_url": self.public})
        if path == "/logout" and method == "POST":
            return self.respond(start, 200, {"ok": True}, extra=[("Set-Cookie", "catalog_session=; Max-Age=0; Path=/; HttpOnly; SameSite=Strict" + ("; Secure" if self.secure else ""))])
        query = parse_qs(env.get("QUERY_STRING", ""))
        if path == "/api/status" and method == "GET":
            sha = query.get("commit", [""])[0]
            if sha and not re.fullmatch(r"[a-f0-9]{40}", sha):
                raise Problem("Invalid publishing reference.")
            return self.respond(start, 200, self.github.status(sha))
        if path == "/api/catalog" and method == "GET":
            key = query.get("catalog", [""])[0]
            if key not in CATALOGS:
                raise Problem("Choose a supported catalog.")
            head, version, catalog = self.github.snapshot(key)
            products = []
            for idx, product in enumerate(catalog["products"]):
                item = dict(product)
                image = item.get("image", "")
                if image.startswith("images/"):
                    item["preview"] = "https://raw.githubusercontent.com/" + self.github.repository + "/" + head + "/" + quote(image)
                else:
                    item["preview"] = image if image.startswith("https://") else ""
                item["idx"] = idx
                products.append(item)
            return self.respond(start, 200, {"version": version, "products": products})
        if path == "/api/product" and method == "POST":
            data = self.body(env)
            return self.respond(start, 200, self.mutate(data, session["user"]))
        raise Problem("Page not found.", 404)

    def mutate(self, data, user):
        key, action = data.get("catalog"), data.get("action")
        if key not in CATALOGS or action not in ("add", "edit", "delete"):
            raise Problem("Invalid catalog or action.")
        operation = data.get("operation", "")
        if not isinstance(operation, str) or not re.fullmatch(r"[a-f0-9-]{36}", operation):
            raise Problem("Reload the form and try again.")
        head, version, catalog = self.github.snapshot(key)
        if action == "add" and any(p.get("upload_id") == operation for p in catalog["products"]):
            return {"ok": True, "commit": head, "message": "This product is already saved. Check publishing for its status."}
        if data.get("version") != version:
            raise Problem("Someone updated this catalog. Reload it before saving; your form is still here.", 409)
        assets = {}
        if action in ("edit", "delete"):
            idx = data.get("idx")
            if type(idx) is not int or not 0 <= idx < len(catalog["products"]):
                raise Problem("This product could not be found. Reload the catalog.", 409)
        if action == "delete":
            catalog["products"].pop(idx)
        else:
            fields = product_fields(data)
            if any(i != data.get("idx") and p.get("name", "").strip().casefold() == fields["name"].casefold()
                   and p.get("sku", "").strip().casefold() == fields["sku"].casefold()
                   for i, p in enumerate(catalog["products"])):
                raise Problem("A product with this name and SKU already exists.", 409)
            if action == "edit":
                product = dict(catalog["products"][idx])
                product.update(fields)
            else:
                product = {**fields, "image": "", "upload_id": operation}
            if data.get("image_data"):
                path, content = read_image(data["image_data"])
                assets[path] = content
                product["image"] = path
            elif data.get("image_url"):
                url = data["image_url"]
                if not isinstance(url, str) or len(url) > 2000:
                    raise Problem("Check the image URL.")
                parts = urlsplit(url)
                if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
                    raise Problem("Use a public HTTPS image URL, or choose an image file.")
                product["image"] = url
            if action == "add":
                catalog["products"].append(product)
            else:
                catalog["products"][idx] = product
        # Public commit history must not expose staff login email addresses.
        staff_id = hmac.new(self.secret.encode(), user.encode(), hashlib.sha256).hexdigest()[:16]
        message = "Catalog admin: " + action + " product in " + key + "\n\nStaff account: " + staff_id + "\nOperation: " + operation
        sha = self.github.commit(key, head, catalog, assets, message)
        return {"ok": True, "commit": sha, "message": "Saved to GitHub. The public catalog is being rebuilt."}


def create_app():
    return CatalogApp()
