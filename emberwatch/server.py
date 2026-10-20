"""Local-only dashboard server; deliberately not a public deployment server."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from .store import Store

STATIC = Path(__file__).parent / 'static'

def serve(database, port):
    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, payload, content_type='application/json'):
            data = json.dumps(payload).encode() if content_type == 'application/json' else payload
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

        def valid_host(self):
            return self.headers.get('Host') in {f'127.0.0.1:{port}', f'localhost:{port}'}

        def do_GET(self):
            if not self.valid_host():
                return self.reply(403, {'error': 'Invalid host'})
            assets = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript'), '/style.css': ('style.css', 'text/css')}
            if self.path in assets:
                name, mime = assets[self.path]
                return self.reply(200, (STATIC/name).read_bytes(), mime)
            store = Store(database)
            try:
                if self.path == '/api/incidents':
                    self.reply(200, store.incidents())
                elif self.path == '/api/export':
                    self.reply(200, store.geojson())
                elif self.path == '/api/health':
                    self.reply(200, {'status': 'ok', 'version': '0.1.0'})
                else:
                    self.reply(404, {'error': 'Not found'})
            finally:
                store.close()

        def do_POST(self):
            if not self.valid_host() or self.headers.get('Origin') != 'http://' + self.headers.get('Host', ''):
                return self.reply(403, {'error': 'Same-origin requests required'})
            if self.path != '/api/review':
                return self.reply(404, {'error': 'Not found'})
            store = Store(database)
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 8192:
                    raise ValueError('Request body must be 1–8192 bytes')
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError('Expected a JSON object')
                if not all(isinstance(data.get(k), str) for k in ['id', 'action', 'note']):
                    raise ValueError('id, action and note must be strings')
                store.review(data['id'], data['action'], data['note'])
                self.reply(200, {'ok': True})
            except (ValueError, UnicodeDecodeError) as exc:
                self.reply(400, {'error': str(exc)})
            finally:
                store.close()
    server = HTTPServer(('127.0.0.1', port), Handler)
    server.timeout = 10
    print(f'EmberWatch: http://127.0.0.1:{port} (Ctrl+C to stop)', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
