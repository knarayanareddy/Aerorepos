import json
import sqlite3
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

from server.app import handler_for, load_index


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'data/trees').mkdir(parents=True)
        (self.root / 'index.html').write_text('hello')
        self.catalog = {'snapshot': '2026-01-01', 'projects': [{'id': 'owner/repo'}]}
        (self.root / 'data/catalog.json').write_text(json.dumps(self.catalog))
        self.snapshot = {'id': 'owner/repo', 'revision': 'abc', 'files': ['src/main.py']}
        (self.root / 'data/trees/owner__repo.json').write_text(json.dumps(self.snapshot))
        self.db = self.root / 'test.sqlite3'
        self.assertEqual(load_index(self.db, self.root), 1)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(self.db, self.root))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def get(self, path):
        with urlopen(self.url + path) as response:
            return response.read()

    def test_catalog_and_snapshot(self):
        self.assertEqual(json.loads(self.get('/api/catalog')), self.catalog)
        self.assertEqual(json.loads(self.get('/api/snapshot?' + urlencode({'repo': 'owner/repo'}))), self.snapshot)
        self.assertEqual(self.get('/'), b'hello')

    def test_missing_and_private_paths(self):
        for path in ('/api/snapshot?repo=missing', '/.git/config', '/data/test.sqlite3', '/server/app.py', '/%2e%2e/server/app.py'):
            with self.subTest(path=path), self.assertRaises(HTTPError) as error:
                self.get(path)
            self.assertEqual(error.exception.code, 404)

    def test_refresh_removes_stale_rows_and_bad_input_does_not_destroy_old_index(self):
        (self.root / 'data/trees/owner__repo.json').write_text('{bad')
        with self.assertRaises(ValueError):
            load_index(self.db, self.root)
        with sqlite3.connect(self.db) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM snapshots').fetchone()[0], 1)
        (self.root / 'data/trees/owner__repo.json').unlink()
        self.assertEqual(load_index(self.db, self.root), 0)
        with sqlite3.connect(self.db) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM snapshots').fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
