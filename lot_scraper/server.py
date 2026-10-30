"""Локальный сервер: отдаёт сайт (index/classifier/codifier/scraper.html) и API выгрузки лотов.
Запуск:  python lot_scraper/server.py [порт]     (по умолчанию 3457)   или  запустить-выгрузку-лотов.bat
Слушает только 127.0.0.1, наружу не открывается. В публичный сайт (_site) не попадает."""
import json, sys, threading, time, webbrowser
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

import engine

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PORT = next((int(a) for a in sys.argv[1:] if a.isdigit()), 3457)

JOB_LOCK = threading.Lock()
JOB = {'state': 'idle', 'items': {}, 'files': None, 'summary': None, 'started': None, 'finished': None,
       'error': None, 'mode': None}


def _item(key):
    return JOB['items'].setdefault(key, {'state': 'pending'})


def _on_update(key, state, result):
    with JOB_LOCK:
        it = _item(key)
        it['state'] = state
        if result is not None:
            it['lots'] = len(result.lots)
            it['no_price'] = sum(1 for lot in result.lots if not lot['price_total'])
            it['no_area'] = sum(1 for lot in result.lots if not lot['area'])
            it['error'] = result.error
            it['notes'] = result.notes[:3]


def _job(targets, label):
    try:
        results = engine.run_targets(targets, _on_update)
        with JOB_LOCK:
            JOB['state'] = 'exporting'
        raw, table, st = engine.export(results, label)
        with JOB_LOCK:
            JOB['files'] = {'table': table, 'raw': raw}
            JOB['summary'] = {**engine.summary(results), **st}
            JOB['state'] = 'done'
    except Exception as e:                           # noqa: BLE001 - показать ошибку в интерфейсе
        with JOB_LOCK:
            JOB['state'] = 'failed'
            JOB['error'] = f'{type(e).__name__}: {e}'
    finally:
        with JOB_LOCK:
            JOB['finished'] = time.time()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    # --- защита: только свой хост, без чтения служебных папок
    def _host_ok(self):
        host = (self.headers.get('Host') or '').split(':')[0]
        return host in ('localhost', '127.0.0.1')

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self._host_ok():
            return self.send_error(HTTPStatus.FORBIDDEN)
        u = urlparse(self.path)
        if u.path == '/api/catalog':
            return self._json({'port': PORT, 'items': engine.catalog()})
        if u.path == '/api/status':
            with JOB_LOCK:
                return self._json(JOB)
        if u.path == '/api/file':
            name = Path(unquote(parse_qs(u.query).get('name', [''])[0])).name   # только имя файла, без путей
            f = engine.OUT / name
            if not name or not f.is_file() or f.suffix != '.xlsx':
                return self.send_error(HTTPStatus.NOT_FOUND)
            data = f.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            self.send_header('Content-Disposition', "attachment; filename*=UTF-8''" + __import__('urllib.parse').parse.quote(name))
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        first = u.path.strip('/').split('/')[0]
        if first in ('lot_scraper', 'scripts', 'tests', '.git', '.github', '.claude'):
            return self.send_error(HTTPStatus.NOT_FOUND)       # исходники и результаты отдаём только через /api
        return super().do_GET()

    def do_POST(self):
        if not self._host_ok() or 'application/json' not in (self.headers.get('Content-Type') or ''):
            return self.send_error(HTTPStatus.FORBIDDEN)
        origin = self.headers.get('Origin')
        if origin and urlparse(origin).hostname not in ('localhost', '127.0.0.1'):
            return self.send_error(HTTPStatus.FORBIDDEN)
        if urlparse(self.path).path != '/api/run':
            return self.send_error(HTTPStatus.NOT_FOUND)
        try:
            req = json.loads(self.rfile.read(int(self.headers.get('Content-Length') or 0)) or b'{}')
        except ValueError:
            return self._json({'error': 'плохой JSON'}, 400)
        mode = req.get('mode')
        parsers = {engine.key_of(t['project_id'], t['sub_id']): t for t in engine.T}
        if mode == 'all':
            chosen, label = list(parsers.values()), ''
        elif mode == 'selected':
            keys = [k for k in req.get('keys', []) if k in parsers]
            chosen, label = [parsers[k] for k in keys], '_выборка'
        else:
            return self._json({'error': 'mode должен быть all или selected'}, 400)
        if not chosen:
            return self._json({'error': 'не выбрано ни одного корпуса с парсером'}, 400)
        with JOB_LOCK:
            if JOB['state'] in ('running', 'exporting'):
                return self._json({'error': 'выгрузка уже идёт'}, 409)
            JOB.update(state='running', items={engine.key_of(t['project_id'], t['sub_id']): {'state': 'pending'}
                                                for t in chosen},
                       files=None, summary=None, error=None, started=time.time(), finished=None, mode=mode)
        threading.Thread(target=_job, args=(chosen, label), daemon=True).start()
        return self._json({'started': len(chosen)})

    def log_message(self, fmt, *args):               # тише в консоли
        if '/api/status' not in str(args[0] if args else ''):
            super().log_message(fmt, *args)


if __name__ == '__main__':
    srv = ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
    url = f'http://localhost:{PORT}/scraper.html'
    print(f'Выгрузка лотов: {url}   (Ctrl+C — остановить)')
    if '--no-browser' not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
