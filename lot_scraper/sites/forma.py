"""workplace.forma.ru/list?projects=<id>[&page=N]: Next.js, лоты в __NEXT_DATA__ (initialState.catalog.flats), 21 на странице.
price — цена, которую показывает сайт; «Выгодная цена N%» (benefits.cash) — акция при полной оплате, идёт в пометки.
Забронированные (status=reserve) берём, но помечаем. Номер страницы — параметр page (проверяется по currentPage в ответе)."""
import re, json
from core import get, num, Result

_cache = {}
MAX_PAGES = 40
ND = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


def _page(project, n):
    url = f'https://workplace.forma.ru/list?projects={project}' + (f'&page={n}' if n > 1 else '')
    m = ND.search(get(url, timeout=40).text)
    if not m:
        raise RuntimeError('нет __NEXT_DATA__ на странице ' + url)
    return json.loads(m.group(1))['props']['pageProps']['initialState']['catalog']


def _load(project):
    if project in _cache:
        return _cache[project]
    flats, seen, notes = [], set(), []
    first = _page(project, 1)
    total = first.get('total') or 0
    pages = (first.get('pagination') or {}).get('countPage') or 1
    for n in range(1, min(pages, MAX_PAGES) + 1):
        c = first if n == 1 else _page(project, n)
        new = [x for x in c.get('flats', []) if x['id'] not in seen]
        if n > 1 and ((c.get('pagination') or {}).get('currentPage') != n or not new):
            notes.append(f'страница {n} не открылась отдельно (сайт отдал currentPage={(c.get("pagination") or {}).get("currentPage")})')
            break
        seen.update(x['id'] for x in new)
        flats += new
    _cache[project] = (flats, total, notes)
    return _cache[project]


def run(t):
    r = Result(t)
    try:
        flats, total, notes = _load(t['forma_project'])
    except Exception as e:                           # noqa: BLE001
        r.error = str(e)
        return r
    r.notes += notes
    for x in flats:
        if t.get('forma_bulk') and str(x.get('bulk_id')) != str(t['forma_bulk']):
            continue
        flags = []
        if x.get('status') == 'reserve':
            flags.append('забронирован на сайте')
        for b in (x.get('benefits') or {}).get('cash') or []:
            if b.get('benefitPrice') and b.get('name'):
                flags.append(f"{b['name']}: {b['benefitPrice']:,.0f} ₽ при полной оплате".replace(',', ' '))
        if x.get('redPrice'):
            flags.append('красная цена на сайте')
        a = x.get('attributes') or {}
        finish = 'Без отделки' if a.get('unfinished') else 'С отделкой' if a.get('finish') else None
        r.add(lot_id=x.get('number') or x.get('id'), lot_name='Офис', area=num(x.get('area')), floor=x.get('floor'),
              finish=finish, status='В продаже', price_total=num(x.get('price')), price_m2=num(x.get('meterPrice')),
              url=f"https://workplace.forma.ru/flat/{x['id']}", flags='; '.join(dict.fromkeys(flags)) or None)
    if total and total != len(flats):
        r.notes.append(f'сайт заявил {total}, получено {len(flats)}')
        if notes:                                    # частичная выгрузка хуже честной ошибки: не подсовываем 21 лот вместо 75
            r.error = f'получена только первая страница из {total} лотов: параметр page не сработал'
    return r
