#!/usr/bin/env python3
"""Read-only Aerorepos HTTP API and static frontend, backed by SQLite."""
import argparse
import json
import os
import sqlite3
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
STATIC = {'/': ('index.html', 'text/html; charset=utf-8'),
          '/index.html': ('index.html', 'text/html; charset=utf-8'),
          '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
          '/map.js': ('map.js', 'text/javascript; charset=utf-8'),
          '/repository.js': ('repository.js', 'text/javascript; charset=utf-8'),
          '/style.css': ('style.css', 'text/css; charset=utf-8')}


def load_index(db_path, root=ROOT):
    """Atomically replace the DB index from the catalog and available snapshots."""
    root = Path(root)
    catalog = json.loads((root / 'data/catalog.json').read_text(encoding='utf-8'))
    if not isinstance(catalog.get('projects'), list):
        raise ValueError('Invalid catalog')
    rows = []
    for project in catalog['projects']:
        repo_id = project['id']
        if repo_id.count('/') != 1 or any(x in repo_id for x in ('..', '\\')):
            raise ValueError(f'Invalid repository ID: {repo_id}')
        path = root / 'data/trees' / (repo_id.replace('/', '__') + '.json')
        if not path.is_file():
            continue
        raw = path.read_text(encoding='utf-8')
        snapshot = json.loads(raw)
        if snapshot.get('id') != repo_id or not isinstance(snapshot.get('files'), list):
            raise ValueError(f'Invalid snapshot: {repo_id}')
        rows.append((repo_id, raw))
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as db:
        db.execute('CREATE TABLE IF NOT EXISTS snapshots (id TEXT PRIMARY KEY, body TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        with db:
            db.execute('DELETE FROM snapshots')
            db.executemany('INSERT INTO snapshots (id, body) VALUES (?, ?)', rows)
            db.execute('INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)',
                       ('catalog', json.dumps(catalog, ensure_ascii=False)))
    return len(rows)


def handler_for(db_path, root=ROOT):
    root = Path(root)
    class Handler(BaseHTTPRequestHandler):
        def send_body(self, code, content_type, data):
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(data)

        def json_response(self, code, value):
            self.send_body(code, 'application/json; charset=utf-8', json.dumps(value, ensure_ascii=False).encode())

        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            request = urlsplit(self.path)
            if request.path == '/runtime-config.js':
                return self.send_body(200, 'text/javascript; charset=utf-8', b'window.AEROREPOS_STATIC = false;\n')
            if request.path == '/api/health':
                return self.json_response(200, {'status': 'ok'})
            if request.path in ('/api/catalog', '/api/snapshot'):
                with sqlite3.connect(db_path) as db:
                    if request.path == '/api/catalog':
                        row = db.execute('SELECT value FROM metadata WHERE key = ?', ('catalog',)).fetchone()
                    else:
                        repo = parse_qs(request.query).get('repo', [''])[0]
                        row = db.execute('SELECT body FROM snapshots WHERE id = ?', (repo,)).fetchone()
                if row is None:
                    return self.json_response(404, {'error': 'Not found'})
                return self.send_body(200, 'application/json; charset=utf-8', row[0].encode())
            # Explicit allowlist: don't expose the database, source scripts or .git.
            entry = STATIC.get(unquote(request.path))
            if entry:
                path = root / entry[0]
                return self.send_body(200, entry[1], path.read_bytes())
            return self.json_response(404, {'error': 'Not found'})
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--db', default=str(ROOT / 'data/aerorepos.sqlite3'))
    args = parser.parse_args()
    count = load_index(args.db)
    server = ThreadingHTTPServer((args.host, args.port), handler_for(args.db))
    print(f'Indexed {count} repository snapshots. Listening on {args.host}:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == '__main__':
    main()
