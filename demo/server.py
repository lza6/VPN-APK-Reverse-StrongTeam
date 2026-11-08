import json, sys
from http.server import HTTPServer, BaseHTTPRequestHandler
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DATA = json.load(open(r'D:\apk-analysis\demo\data.json', encoding='utf-8'))
PAGE = open(r'D:\apk-analysis\demo\index.html', encoding='utf-8').read()

class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        p = self.path
        if p == '/api/data':
            b = json.dumps(DATA, ensure_ascii=False).encode()
            self._send(200, b, 'application/json; charset=utf-8')
        elif p == '/api/health':
            self._send(200, b'{"ok":true}', 'application/json')
        elif p in ('/', '/index.html'):
            self._send(200, PAGE.encode(), 'text/html; charset=utf-8')
        else:
            self._send(404, b'not found', 'text/plain')

print('demo on http://127.0.0.1:8951')
HTTPServer(('127.0.0.1', 8951), H).serve_forever()
