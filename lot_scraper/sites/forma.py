"""workplace.forma.ru: каталог грузится POST-ом на manager.forma.ru/api/v2/marketplace (JSON, без куки), 21 лот на странице, page=1..countPage.
Страница списка с &page=N на сервере всегда отдаёт первые 21 лот, поэтому читаем API напрямую. Фильтр floor.min=2 — как у сайта по умолчанию: первый этаж там розница, в Q3 офисов на 1 этаже нет (кроме 1 лота Lakes 2).
price — цена, которую показывает сайт; «Выгодная цена N%» (benefits.cash) — акция при полной оплате, идёт в пометки.
Забронированные (status=reserve) берём, но помечаем."""
import time, requests
from core import HEAD, num, Result

_cache = {}
MAX_PAGES = 40
API = 'https://manager.forma.ru/api/v2/marketplace'
LIMIT = 21


def _post(project, page):
    body = {'projects': [int(project)], 'price': {}, 'area': {}, 'floor': {'min': 2}, 'attributes': [], 'page': page, 'limit': LIMIT,
            'order': {'key': 'area', 'type': 'asc'}, 'type': 4, 'objectType': 'commercial', 'ceilingHeight': {},
            'sanpinPeopleCount': {}}
    hdr = {**HEAD, 'Accept': 'application/json', 'Origin': 'https://workplace.forma.ru',
           'Referer': f'https://workplace.forma.ru/list?projects={project}'}
    last = None
    for i in range(3):
        try:
            r = requests.post(API, json=body, headers=hdr, timeout=40)
            if r.status_code in (200, 201):
                return r.json()
            last = f'HTTP {r.status_code}'
        except Exception as e:                       # noqa: BLE001
            last = type(e).__name__
        time.sleep(1.5 * (i + 1))
    raise RuntimeError(f'{API} (projects={project}, page={page}): {last}')


def _load(project):
    if project in _cache:
        return _cache[project]
    flats, seen, notes, total = [], set(), [], 0
    page, pages = 1, 1
    while page <= min(pages, MAX_PAGES):
        d = _post(project, page)
        total, pages = d.get('total') or total, d.get('countPage') or 1
        new = [x for x in d.get('flats', []) if x['id'] not in seen]
        if not new:
            notes.append(f'страница {page} пустая или повторяет предыдущие')
            break
        seen.update(x['id'] for x in new)
        flats += new
        page += 1
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
            r.error = f'получено {len(flats)} из {total} лотов: {notes[0]}'
    return r
