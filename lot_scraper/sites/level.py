"""business.level.ru: GET /api/filter/?category=office&project=<slug>&limit&offset (JSON, без куки).
price — цена, которую показывает сайт (с учётом скидки застройщика), old_price — до скидки; ppm — ₽/м² по цене price."""
from core import get, num, Result

_cache = {}
PAGE = 100


def _load(slug):
    if slug not in _cache:
        res, offset = [], 0
        while True:
            d = get(f'https://business.level.ru/api/filter/?type_of_advertisement=0&category=office&project={slug}'
                    f'&limit={PAGE}&offset={offset}&city=moscow', timeout=40, headers={'Accept': 'application/json'}).json()
            res += d.get('results', [])
            offset += PAGE
            if not d.get('next') or not d.get('results'):
                break
        _cache[slug] = (res, d.get('count', len(res)))
    return _cache[slug]


def run(t):
    r = Result(t)
    try:
        res, count = _load(t['level_project'])
    except Exception as e:                           # noqa: BLE001
        r.error = str(e)
        return r
    for x in res:
        if t.get('level_building') and str(x.get('building_number')) != str(t['level_building']):
            continue
        flags = []
        if x.get('old_price') and x.get('price') and x['old_price'] != x['price']:
            flags.append(f"цена до скидки {x['old_price']:,.0f} ₽ (скидка {x.get('discount')}%)".replace(',', ' '))
        for s in x.get('commercial_shields') or []:
            if s.get('name'):
                flags.append('на сайте: ' + s['name'])
        if not x.get('show_price', True):
            flags.append('сайт скрывает цену')
        r.add(lot_id=x.get('article') or x.get('pk'), lot_name=x.get('functional_purpose_text') or 'Офис',
              area=num(x.get('actual_area') or x.get('area')), floor=x.get('floor'), status='В продаже',
              price_total=num(x.get('price')) if x.get('show_price', True) else None, price_m2=num(x.get('ppm')),
              url=t['url'], flags='; '.join(dict.fromkeys(flags)) or None)
    if count != len(res):
        r.notes.append(f'сайт заявил {count}, получено {len(res)}')
    return r
