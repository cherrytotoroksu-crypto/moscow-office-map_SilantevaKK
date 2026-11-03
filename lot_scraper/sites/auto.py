"""Универсальный сборщик для корпусов без своего парсера: открывает страницу как обычный посетитель (Chromium),
записывает JSON-ответы и встроенный в HTML JSON, находит в них массив лотов (autodetect), добирает страницы списка
GET-запросами с page/offset/from, если ответ явно постраничный. Все лоты помечаются «автоопределение»: на странице
может быть несколько корпусов или лишние объекты — результат нужно сверить. Свой парсер, если он есть, имеет приоритет."""
import os, re, json, time
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
import requests
import autodetect as A
from core import HEAD, Result

SKIP_HOSTS = ('yandex', 'google', 'doubleclick', 'facebook', 'vk.com', 'rutube', 'mail.ru', 'top.mail', 'gstatic',
              'googletagmanager', 'metrika', 'calltouch', 'roistat', 'jivo', 'carrotquest', 'tiktok', 'clarity.ms',
              'comagic', 'uiscom', 'adriver', 'smartcallback')
PAGE_PARAMS = ('page', 'offset', 'from', 'skip', 'start')
MORE_TEXT = re.compile(r'^(показать ещё|показать еще|загрузить ещё|загрузить еще|ещё|еще|показать все|смотреть все)', re.I)


def _capture(url):
    from playwright.sync_api import sync_playwright
    bodies, blobs = [], []
    proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    with sync_playwright() as p:
        b = p.chromium.launch(proxy={'server': proxy} if proxy else None)
        pg = b.new_page()

        def on(r):
            q = r.request
            if q.resource_type not in ('xhr', 'fetch', 'document') or any(h in urlparse(r.url).netloc for h in SKIP_HOSTS):
                return
            ctype = (r.headers.get('content-type') or '').lower()
            try:
                body = r.body()
            except Exception:                                    # noqa: BLE001
                return
            if len(body) > 6_000_000:
                return
            if 'json' in ctype:
                try:
                    bodies.append((r.url, q.method, json.loads(body)))
                except ValueError:
                    pass
            elif 'html' in ctype:
                blobs.append(body.decode('utf-8', 'ignore'))

        pg.on('response', on)
        pg.goto(url, wait_until='domcontentloaded', timeout=60000)
        pg.wait_for_timeout(4000)
        for _ in range(8):                                       # дозагрузка прокруткой
            pg.mouse.wheel(0, 4000)
            pg.wait_for_timeout(1000)
        for _ in range(15):                                      # кнопки «Показать ещё»
            btn = next((e for e in pg.query_selector_all('button, a, div[role=button]')
                        if e.is_visible() and MORE_TEXT.match((e.inner_text() or '').strip())), None)
            if not btn:
                break
            try:
                btn.click(timeout=3000)
            except Exception:                                    # noqa: BLE001
                break
            pg.wait_for_timeout(1800)
        blobs.append(pg.content())
        b.close()
    return bodies, blobs


def _more_pages(url, first_rows, path):
    """Если ответ получен GET-ом с параметром страницы — запросить следующие, пока приходят новые строки."""
    u = urlparse(url)
    q = dict(parse_qsl(u.query))
    key = next((k for k in PAGE_PARAMS if k in q), None)
    if not key:
        return []
    try:
        cur = int(q[key])
    except ValueError:
        return []
    size = len(first_rows)
    seen = {json.dumps(x, sort_keys=True, default=str) for x in first_rows}
    out = []
    for _ in range(60):
        cur = cur + size if key in ('offset', 'from', 'skip', 'start') else cur + 1
        q[key] = str(cur)
        try:
            d = requests.get(urlunparse(u._replace(query=urlencode(q))), headers={**HEAD, 'Accept': 'application/json'}, timeout=40).json()
        except Exception:                                        # noqa: BLE001
            break
        got = next((arr for p2, arr, _s in A.find_lot_arrays(d) if p2 == path), None)
        new = [x for x in (got or []) if json.dumps(x, sort_keys=True, default=str) not in seen]
        if not new:
            break
        seen.update(json.dumps(x, sort_keys=True, default=str) for x in new)
        out += new
        time.sleep(0.4)
    return out


def run(t):
    r = Result(t)
    try:
        bodies, blobs = _capture(t['url'])
    except Exception as e:                                       # noqa: BLE001
        r.error = f"{type(e).__name__}: {str(e)[:120]}"
        return r
    cands = []
    for url, method, obj in bodies:
        cands += [(s['score'], url, method, p, arr, s) for p, arr, s in A.find_lot_arrays(obj)[:2]]
    for h in blobs:
        for obj in A.json_blobs(h):
            cands += [(s['score'], t['url'], 'HTML', p, arr, s) for p, arr, s in A.find_lot_arrays(obj)[:2]]
    if not cands:
        r.error = 'автоопределение: данных, похожих на лоты, нет (сайт мог отдать пустой список или данные не в JSON; нужен отдельный парсер или проверка вручную)'
        return r
    cands.sort(key=lambda x: -x[0])
    _sc, url, method, path, arr, sch = cands[0]
    rows = list(arr)
    if method == 'GET':
        rows += _more_pages(url, arr, path)
    r.notes.append(f'автоопределение: {len(rows)} строк из {urlparse(url).path[:60]} {path}; поля: площадь={sch["area"]}, '
                   f'цена={sch["price"] or sch["price_m2"]}, этаж={sch["floor"]}, номер={sch["id"]}')
    rows, fnotes = A.filter_rows(rows, t['corpus'], t['project'])
    r.notes += fnotes
    for lot in A.to_lots(rows, sch):
        st = str(lot.pop('_status') or '').lower()
        if re.search(r'sold|продан|booked|reserv|брон|unavailable', st):
            continue
        r.add(lot_name='Офис', status='В продаже', url=t['url'],
              flags='автоопределение: проверить корпус и цену', **lot)
    return r
