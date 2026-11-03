"""upside-yamskaya.ru: GET /api/commercial/filter/complexes/<uuid>/buildings/<n> (этажи со счётчиками) ->
.../buildings/<n>/floors/<этаж> (real_estates). JSON без куки. price — цена сайта, old_price — до скидки."""
from core import get, num, Result

BASE = 'https://upside-yamskaya.ru/api/commercial/filter/complexes/'
Q = '?status=free&status=booked&offer_type=sale'
HDR = {'Accept': 'application/json'}


def run(t):
    r = Result(t)
    base = f"{BASE}{t['ay_complex']}/buildings/{t['ay_building']}"
    try:
        b = get(base + Q, timeout=40, headers=HDR).json()
        floors = [f['floor_number'] for f in b.get('floors', []) if f.get('total_count')]
        items = []
        for n in floors:
            items += get(f'{base}/floors/{n}{Q}', timeout=40, headers=HDR).json().get('real_estates', [])
    except Exception as e:                           # noqa: BLE001
        r.error = str(e)
        return r
    for x in items:
        if x.get('purpose') != 'office' or 'sale' not in (x.get('offer_types') or ['sale']):
            continue
        flags = []
        if x.get('status') == 'booked':
            flags.append('забронирован на сайте')
        if x.get('has_discount') and x.get('old_price'):
            flags.append(f"цена до скидки {num(x['old_price']):,.0f} ₽".replace(',', ' '))
        r.add(lot_id=x.get('number'), lot_name='Офис', area=num(x.get('total_area')), floor=x.get('floor_number'), status='В продаже',
              price_total=num(x.get('price')), url=t['url'], flags='; '.join(flags) or None)
    expected = b.get('total_count')
    if expected is not None and expected != len(r.lots):
        r.notes.append(f'сайт заявил {expected}, взято {len(r.lots)}')
    return r
