"""upside-business.ru (Upside Кунцево): GET /local/app/api/flats/list.php (Bitrix, JSON, без куки).
Берём продажу (RENT=N) со статусом AVAILABLE; корпус — PROPERTIES.BUILDING (korpus-1/korpus-2)."""
from core import get, num, Result

_cache = {}
PER = 100


def _load():
    if 'all' not in _cache:
        rows, page = [], 1
        while True:
            d = get('https://upside-business.ru/local/app/api/flats/list.php?RENT=N&STATUS=AVAILABLE&sort_field=PROPERTY_REAL_PRICE'
                    f'&sort_type=asc&filter=1&page={page}&per_page={PER}', timeout=40, headers={'Accept': 'application/json'}).json()
            rows += d.get('FLATS', [])
            if len(d.get('FLATS', [])) < PER or len(rows) >= num(d.get('COUNT_FILTERED') or 0):
                break
            page += 1
        _cache['all'] = (rows, d.get('COUNT_FILTERED'), d.get('COUNT_ALL'))
    return _cache['all']


def run(t):
    r = Result(t)
    try:
        rows, filtered, total_all = _load()
    except Exception as e:                           # noqa: BLE001
        r.error = str(e)
        return r
    for x in rows:
        p = x.get('PROPERTIES') or {}
        if p.get('BUILDING') != t['ub_building'] or p.get('SOLD') == 'Y' or p.get('STATUS') != 'AVAILABLE':
            continue
        r.add(lot_id=p.get('NUM_PRINT') or p.get('NUM'), lot_name='Офис', area=num(p.get('SQ')), floor=num(p.get('FLOOR')),
              finish=p.get('FINISHING') or None, status='В продаже', price_total=num(p.get('PRICE') or p.get('REAL_PRICE')),
              price_m2=num(p.get('PRICE_SQM')), url=t['url'])
    r.notes.append(f'на сайте всего {total_all}, в продаже и не в аренду {filtered}')
    return r
