"""Снимок страниц для разведки: открывает сайты как обычный посетитель и сохраняет в папку recon/
готовый HTML и ответы всех запросов страницы (JSON и HTML). По этим файлам потом пишется парсер.

Запуск (с включённым VPN, если сайт открывается только через него):
    python lot_scraper/recon_dump.py                 все корпуса без парсера, у которых есть ссылка
    python lot_scraper/recon_dump.py URL [URL ...]   только указанные страницы
Прокси: переменная HTTPS_PROXY (если VPN работает через прокси). Результат: lot_scraper/recon/ (в git не попадает).
"""
import sys, os, re, json, hashlib, datetime
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.stdout.reconfigure(encoding='utf-8')

SKIP_HOSTS = ('yandex', 'google', 'doubleclick', 'facebook', 'vk.com', 'rutube', 'mail.ru', 'top.mail', 'gstatic',
              'googletagmanager', 'metrika', 'calltouch', 'roistat', 'jivo', 'carrotquest', 'tiktok', 'clarity.ms')
TEXT_TYPES = ('json', 'html', 'xml', 'text/plain', 'javascript')
MAX_BODY = 3_000_000
MAX_RESP = 80


def slug(url):
    p = urlparse(url)
    s = re.sub(r'[^\w.-]+', '_', (p.netloc + p.path))[:60].strip('_')
    return f'{s}_{hashlib.md5(url.encode()).hexdigest()[:6]}'


def dump(pw, url, out_root):
    d = out_root / slug(url)
    d.mkdir(parents=True, exist_ok=True)
    proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    b = pw.chromium.launch(proxy={'server': proxy} if proxy else None)
    pg = b.new_page()
    log, saved = [], []

    def on(r):
        q = r.request
        host = urlparse(r.url).netloc
        if any(h in host for h in SKIP_HOSTS) or len(saved) >= MAX_RESP:
            return
        if q.resource_type not in ('xhr', 'fetch', 'document'):
            return
        ctype = (r.headers.get('content-type') or '').lower()
        row = {'method': q.method, 'url': r.url[:900], 'status': r.status, 'type': q.resource_type,
               'content_type': ctype, 'post': (q.post_data or '')[:600]}
        if any(t in ctype for t in TEXT_TYPES):
            try:
                body = r.body()
                if len(body) <= MAX_BODY:
                    name = f'resp_{len(saved):02d}' + ('.json' if 'json' in ctype else '.html' if 'html' in ctype else '.txt')
                    (d / name).write_bytes(body)
                    row['file'], row['bytes'] = name, len(body)
                    saved.append(name)
            except Exception as e:                       # noqa: BLE001
                row['body_error'] = str(e)[:80]
        log.append(row)

    pg.on('response', on)
    err = None
    try:
        pg.goto(url, wait_until='domcontentloaded', timeout=60000)
        pg.wait_for_timeout(4000)
        for _ in range(8):                               # дозагрузка прокруткой
            pg.mouse.wheel(0, 4000)
            pg.wait_for_timeout(1200)
        (d / 'page_rendered.html').write_text(pg.content(), encoding='utf-8')
        try:
            pg.screenshot(path=str(d / 'page.png'), full_page=False)
        except Exception:                                # noqa: BLE001
            pass
    except Exception as e:                               # noqa: BLE001
        err = f'{type(e).__name__}: {str(e)[:160]}'
    finally:
        b.close()
    (d / 'requests.json').write_text(json.dumps({'url': url, 'error': err, 'requests': log}, ensure_ascii=False, indent=1),
                                     encoding='utf-8')
    return d.name, err, len(log)


def main():
    from playwright.sync_api import sync_playwright
    args = sys.argv[1:]
    if args:
        urls = args
    else:
        import engine
        seen, urls = set(), []
        for r in engine.catalog():
            if not r['has_parser'] and r['url'] and r['url'] not in seen:
                seen.add(r['url'])
                urls.append(r['url'])
    out_root = HERE / 'recon' / datetime.date.today().strftime('%Y-%m-%d')
    out_root.mkdir(parents=True, exist_ok=True)
    print(f'Страниц: {len(urls)}. Папка: {out_root}')
    index = []
    with sync_playwright() as pw:
        for i, u in enumerate(urls, 1):
            name, err, n = dump(pw, u, out_root)
            print(f'[{i}/{len(urls)}] {"ОШИБКА " + err if err else "ok, запросов " + str(n)}  {u}')
            index.append({'url': u, 'folder': name, 'error': err, 'requests': n})
            (out_root / 'index.json').write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding='utf-8')
    ok = sum(1 for x in index if not x['error'])
    print(f'Готово: {ok} из {len(index)} страниц сняты. Папку recon целиком можно показать Claude.')


if __name__ == '__main__':
    main()
