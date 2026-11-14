import base64
import copy
import io
import json
import time
import unittest
from unittest.mock import patch
from hosted.app import CatalogApp, GitHub, MAX_BODY, Problem, password_hash, read_image


class FakeGitHub:
    repository = "owner/catalog"
    def __init__(self):
        self.catalog = {"name": "Jewellery", "products": [{"name": "Original", "sku": "RS100", "price": "Rs. 1000",
            "description": "Original description", "image": "images/existing.png", "category": "Necklaces",
            "best_seller": True, "extra_preserved_field": "keep"}]}
        self.head, self.version = "a" * 40, "b" * 40
        self.writes, self.assets, self.fail = [], {}, False
    def snapshot(self, key):
        return self.head, self.version, copy.deepcopy(self.catalog)
    def commit(self, key, head, catalog, assets, message):
        if self.fail:
            raise Problem("GitHub is unavailable", 502)
        self.catalog, self.assets = catalog, assets
        self.head, self.version = "c" * 40, "d" * 40
        self.writes.append(message)
        return self.head
    def status(self, sha):
        return {"state": "building", "message": "Publishing"}


class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hashed = password_hash("a-strong-test-password")
    def setUp(self):
        self.github = FakeGitHub()
        self.app = CatalogApp({"SESSION_SECRET": "x" * 40, "STAFF_ACCOUNTS_JSON": json.dumps({"staff@example.com": self.hashed})}, self.github)
        self.payload = {"user": "staff@example.com", "expires": int(time.time()) + 1000, "csrf": "csrf-token",
                        "stamp": __import__('hashlib').sha256(self.hashed.encode()).hexdigest()}
        self.cookie = "catalog_session=" + self.app.seal(self.payload)
    def request(self, path, method="GET", data=None, authenticated=True, csrf=True, extra=None):
        raw = b"" if data is None else json.dumps(data).encode()
        route, _, query = path.partition('?')
        env = {"PATH_INFO": route, "QUERY_STRING": query, "REQUEST_METHOD": method, "HTTP_HOST": "admin.example.com",
               "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(raw)), "wsgi.input": io.BytesIO(raw)}
        if authenticated: env["HTTP_COOKIE"] = self.cookie
        if csrf: env["HTTP_X_CSRF_TOKEN"] = "csrf-token"
        env.update(extra or {})
        captured = {}
        def start(status, headers): captured.update(status=int(status.split()[0]), headers=dict(headers))
        content = b"".join(self.app(env, start))
        captured['body'] = json.loads(content) if captured['headers']['Content-Type'] == 'application/json' else content
        return captured
    def product(self, **changes):
        return {"action": "add", "catalog": "mens_jewelry", "version": self.github.version,
                "operation": "12345678-1234-1234-1234-123456789012", "name": "New necklace", "sku": "RS100",
                "description": "Anti tarnish", "price": "1,999.50", "category": "Necklaces", **changes}
    def test_unauthenticated_cannot_read_or_write(self):
        for path, method in [("/api/catalog?catalog=mens_jewelry", "GET"), ("/api/product", "POST"), ("/api/status", "GET")]:
            self.assertEqual(self.request(path, method, {}, False)["status"], 401)
        self.assertEqual(self.github.writes, [])
    def test_login_secure_cookie_and_bad_credentials(self):
        result = self.request('/login', 'POST', {"email": "staff@example.com", "password": "a-strong-test-password"}, False)
        self.assertEqual(result['status'], 200)
        for flag in ('HttpOnly', 'Secure', 'SameSite=Strict'): self.assertIn(flag, result['headers']['Set-Cookie'])
        result = self.request('/login', 'POST', {"email": "staff@example.com", "password": "bad"}, False)
        self.assertEqual(result['status'], 401)
    def test_login_throttles_and_rejects_cross_origin(self):
        for _ in range(5): self.request('/login', 'POST', {"email": "staff@example.com", "password": "bad"}, False)
        self.assertEqual(self.request('/login', 'POST', {"email": "staff@example.com", "password": "bad"}, False)['status'], 429)
        self.assertEqual(self.request('/login', 'POST', {}, False, extra={"HTTP_ORIGIN": "https://evil.example"})['status'], 403)
    def test_csrf_and_expired_or_tampered_session(self):
        self.assertEqual(self.request('/api/product', 'POST', self.product(), csrf=False)['status'], 403)
        self.payload['expires'] = 0
        self.cookie = 'catalog_session=' + self.app.seal(self.payload)
        self.assertEqual(self.request('/api/session')['status'], 401)
        self.cookie += 'tampered'
        self.assertEqual(self.request('/api/session')['status'], 401)
    def test_removed_account_invalidates_session(self):
        self.app.accounts.clear()
        self.assertEqual(self.request('/api/session')['status'], 401)
    def test_add_is_atomic_and_preserves_existing_product(self):
        original = copy.deepcopy(self.github.catalog['products'][0])
        png = base64.b64encode(b'\x89PNG\r\n\x1a\nexample-image').decode()
        result = self.request('/api/product', 'POST', self.product(image_data='data:image/png;base64,' + png))
        self.assertEqual(result['status'], 200)
        self.assertEqual(self.github.catalog['products'][0], original)
        self.assertEqual(self.github.catalog['products'][1]['price'], 'Rs. 1999.50')
        image = self.github.catalog['products'][1]['image']
        self.assertIn(image, self.github.assets)
        self.assertIn('Staff account:', self.github.writes[0])
        self.assertNotIn('staff@example.com', self.github.writes[0])
    def test_repeat_add_after_timeout_does_not_duplicate(self):
        data = self.product()
        self.assertEqual(self.request('/api/product', 'POST', data)['status'], 200)
        self.assertEqual(self.request('/api/product', 'POST', data)['status'], 200)
        self.assertEqual(len(self.github.writes), 1)
    def test_stale_edit_does_not_overwrite_another_staff_change(self):
        result = self.request('/api/product', 'POST', self.product(action='edit', idx=0, version='old'))
        self.assertEqual(result['status'], 409)
        self.assertEqual(self.github.writes, [])
    def test_edit_preserves_extra_fields_and_unchanged_image(self):
        result = self.request('/api/product', 'POST', self.product(action='edit', idx=0))
        self.assertEqual(result['status'], 200)
        self.assertEqual(self.github.catalog['products'][0]['extra_preserved_field'], 'keep')
        self.assertEqual(self.github.catalog['products'][0]['image'], 'images/existing.png')
    def test_invalid_price_or_image_never_commits(self):
        for data in (self.product(price='RS100'), self.product(image_data='data:image/svg+xml;base64,YQ=='),
                     self.product(image_data='data:image/png;base64,YQ=='), self.product(image_url='https://secret:pass@example.com/a.jpg')):
            self.assertEqual(self.request('/api/product', 'POST', data)['status'], 400)
        self.assertEqual(self.github.writes, [])
    def test_remote_failure_is_not_reported_as_saved(self):
        self.github.fail = True
        result = self.request('/api/product', 'POST', self.product())
        self.assertEqual(result['status'], 502)
        self.assertNotIn('ok', result['body'])
        self.assertEqual(len(self.github.catalog['products']), 1)
    def test_bad_index_or_oversized_request_rejected(self):
        self.assertEqual(self.request('/api/product', 'POST', self.product(action='delete', idx=True))['status'], 409)
        self.assertEqual(self.request('/api/product', 'POST', {}, extra={'CONTENT_LENGTH': str(MAX_BODY + 1)})['status'], 413)
    def test_secrets_never_exposed_to_browser(self):
        result = self.request('/api/session')
        self.assertEqual(result['status'], 200)
        self.assertNotIn(self.hashed, json.dumps(result))
        self.assertNotIn('x' * 40, json.dumps(result))
        self.assertEqual(self.request('/.env')['status'], 404)
        self.assertEqual(self.request('/hosted/app.py')['status'], 404)
        self.assertEqual(self.request('/static/../app.py')['status'], 404)
    def test_pages_and_preview_use_exact_remote_commit(self):
        self.assertEqual(self.request('/')['status'], 200)
        data = self.request('/api/catalog?catalog=mens_jewelry')['body']
        self.assertIn('a' * 40, data['products'][0]['preview'])
        self.assertNotIn('mens_accessories', self.request('/api/session')['body']['catalogs'])


class GitHubTests(unittest.TestCase):
    def test_commit_uses_single_non_forced_ref_update_for_catalog_and_image(self):
        github = GitHub('owner/catalog', 'not-a-real-token')
        calls = []
        def fake(method, path, data=None):
            calls.append((method, path, data))
            if path == '/git/commits/' + 'a' * 40: return {'tree': {'sha': 'tree'}}
            return {'sha': 'b' * 40}
        github.call = fake
        github.commit('mens_jewelry', 'a' * 40, {'products': []}, {'images/new.png': b'image'}, 'test')
        tree = next(data for _, path, data in calls if path == '/git/trees')
        self.assertEqual([x['path'] for x in tree['tree']], ['catalogs/mens_jewelry.json', 'images/new.png'])
        self.assertEqual(calls[-1], ('PATCH', '/git/refs/heads/main', {'sha': 'b' * 40, 'force': False}))
    def test_status_distinguishes_waiting_building_success_failure(self):
        github = GitHub('owner/catalog', 'not-a-real-token')
        for status, conclusion, expected in [('in_progress', None, 'building'), ('completed', 'success', 'live'), ('completed', 'failure', 'failed')]:
            github.call = lambda *a: {'workflow_runs': [{'status': status, 'conclusion': conclusion, 'html_url': 'https://github.com/run', 'head_sha': 'a' * 40}]}
            self.assertEqual(github.status('a' * 40)['state'], expected)
        github.call = lambda *a: {'workflow_runs': []}
        self.assertEqual(github.status('a' * 40)['state'], 'waiting')


if __name__ == '__main__':
    unittest.main()
