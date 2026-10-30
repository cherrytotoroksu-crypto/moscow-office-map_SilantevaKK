"""a101.ru: GET /api/commercial/ (JSON, без куки). status 1 = свободно, 4/5 = бронь, 2/3 = продано."""
from core import get, num, Result

_cache = {}


def _load(slug):
    if slug not in _cache:
        url = f'https://a101.ru/api/commercial/?deal=sell&order=actual_price&project={slug}&limit=500&offset=0'
        _cache[slug] = get(url, timeout=40, headers={'Accept': 'application/json',
                                                     'Referer': 'https://a101.ru/commercial/'}).json()
    return _cache[slug]


def run(t):
    r = Result(t)
    try:
        d = _load(t['a101_project'])
    except Exception as e:
        r.error = str(e)
        return r
    skipped = {}
    for x in d.get('results', []):
        if x.get('building') != t['a101_building']:
            continue
        typ = x.get('commercial_type_name') or ''
        if t.get('a101_types') and typ not in t['a101_types']:
            skipped[typ] = skipped.get(typ, 0) + 1
            continue
        if x.get('status') != 1:
            skipped[f"статус {x.get('status')}"] = skipped.get(f"статус {x.get('status')}", 0) + 1
            continue
        r.add(lot_id=x.get('article'), lot_name=typ, area=num(x.get('area')), floor=num(x.get('floor')),
              status='В продаже', price_total=num(x.get('actual_price')), price_m2=num(x.get('actual_ppm')),
              url=t['url'], flags=None if x.get('actual_price') else 'цена не опубликована')
    if skipped:
        r.notes.append('не взято: ' + ', '.join(f'{k}: {v}' for k, v in skipped.items()))
    if d.get('count') is not None and d['count'] != len(d.get('results', [])):
        r.notes.append(f"сайт заявил {d['count']}, получено {len(d['results'])}")
    return r
