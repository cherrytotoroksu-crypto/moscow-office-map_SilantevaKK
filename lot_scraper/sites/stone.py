"""stone.ru: GET /api/lots (JSON, без куки). Один запрос на набор проектов, корпус выбирается по полю housing.
status=1 в фильтре = свободно. Цена selling_price уже со скидкой застройщика; цена до скидки идёт в пометку."""
from core import get, num, Result
from targets import T

_cache = {}
PAGE = 12                      # сайт сам ходит по 12; per_page=100 даёт HTTP 422


def _load(projects, direction):
    key = (projects, direction)
    if key not in _cache:
        lots, offset = [], 0
        while True:
            url = (f'https://stone.ru/api/lots?filter[direction]={direction}&filter[status]=1&sort=lots.selling_price'
                   f'&filter[projects]={projects}' + (f'&from={offset}' if offset else '') + f'&per_page={PAGE}')
            d = get(url, timeout=40, headers={'Accept': 'application/json', 'Referer': 'https://stone.ru/'}).json()
            lots += d.get('data', [])
            total = (d.get('meta') or {}).get('total', len(lots))
            offset += PAGE
            if offset >= total or not d.get('data'):
                break
        _cache[key] = (lots, total)
    return _cache[key]


def run(t):
    r = Result(t)
    try:
        lots, total = _load(t['stone_projects'], t.get('stone_direction', '1,4'))
    except Exception as e:                           # noqa: BLE001
        r.error = str(e)
        return r
    covered = {x.get('stone_housing') for x in T if x['site'] == 'stone'}
    other = {}
    for x in lots:
        if x.get('housing') != t['stone_housing']:
            if x.get('housing') not in covered:        # корпуса без строки в реестре Q3: показываем, чтобы не потерять новое
                other[x.get('housing')] = other.get(x.get('housing'), 0) + 1
            continue
        flags = []
        before, disc = x.get('selling_price_before_discount'), x.get('discount')
        if before and x.get('selling_price') and before != x['selling_price']:
            flags.append(f'цена до скидки {before:,.0f} ₽ (скидка {disc}%)'.replace(',', ' '))
        if not x.get('show_price_flg', True):
            flags.append('сайт скрывает цену')
        r.add(lot_id=x.get('number'), lot_name=x.get('sub_type_name') or x.get('type_name'), area=num(x.get('area')),
              floor=num(x.get('floor')), status='В продаже', price_total=num(x.get('selling_price')),
              price_m2=num(x.get('selling_price_per_meter')), url=t['url'], flags='; '.join(flags) or None)
    if other:
        r.notes.append('на сайте есть корпуса вне реестра Q3: ' + ', '.join(f'{k}: {v}' for k, v in sorted(other.items(), key=lambda i: str(i[0]))))
    if total != len(lots):
        r.notes.append(f'сайт заявил {total}, получено {len(lots)}')
    return r
