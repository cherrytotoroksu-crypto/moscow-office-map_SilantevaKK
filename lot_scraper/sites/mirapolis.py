"""mirapolis.city: GET /api/building-objects/filter?projects[0]=12&layout_types[0]=non-residential (JSON, без куки).
cost — цена до скидки, discount_cost — цена, которую показывает сайт (со скидкой)."""
from core import get, num, Result


def run(t):
    r = Result(t)
    flats, page = [], 1
    try:
        while True:
            d = get(f"https://mirapolis.city/api/building-objects/filter?projects[0]={t['mir_project']}"
                    f"&layout_types[0]=non-residential&page={page}&per_page=100&sort[cost]=asc", timeout=40,
                    headers={'Accept': 'application/json'}).json()['data']
            flats += d.get('flats', [])
            pg = d.get('pagination') or {}
            if page >= (pg.get('last_page') or 1):
                break
            page += 1
    except Exception as e:                           # noqa: BLE001
        r.error = str(e)
        return r
    for x in flats:
        if x.get('status') != 'available':
            continue
        price = x.get('discount_cost') or x.get('cost')
        flags = []
        if x.get('discount_cost') and x.get('cost') and x['cost'] != x['discount_cost']:
            flags.append(f"цена до скидки {x['cost']:,.0f} ₽".replace(',', ' '))
        r.add(lot_id=f"к{x.get('building')}-{x.get('number')}", lot_name=(x.get('properties') or {}).get('name') or 'Офис',
              area=num((x.get('layout') or {}).get('area')), floor=(x.get('floor') or {}).get('number'), status='В продаже',
              price_total=num(price), price_m2=num(x.get('discount_meter_cost') or x.get('meter_cost')), url=t['url'],
              flags='; '.join(flags) or None)
    return r
