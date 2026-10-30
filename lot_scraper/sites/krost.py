"""krost.ru: GET /api/commercial/building/<id>/ (floor_set с total_count) -> /api/commercial/floor/<id>/ (commercial_set), JSON без куки.
Берём только этажи, где total_count > 0, и продажу (deal_type=1) со статусом «свободно» (status=1)."""
from core import get, num, Result

BASE = 'https://krost.ru/api/commercial/'
HDR = {'Accept': 'application/json'}


def run(t):
    r = Result(t)
    try:
        b = get(f"{BASE}building/{t['krost_building']}/", timeout=40, headers=HDR).json()
        floors = [f for f in b.get('floor_set', []) if f.get('total_count')]
        items = []
        for f in floors:
            items += get(f"{BASE}floor/{f['id']}/", timeout=40, headers=HDR).json().get('commercial_set', [])
    except Exception as e:                           # noqa: BLE001
        r.error = str(e)
        return r
    for x in items:
        if x.get('deal_type') != 1 or x.get('status') != 1 or not x.get('available_on_site', True):
            continue
        flags = []
        if x.get('has_discount') and x.get('old_price'):
            flags.append(f"цена до скидки {x['old_price']:,.0f} ₽".replace(',', ' '))
        if x.get('has_special_offer'):
            flags.append('на сайте спецпредложение')
        hidden = x.get('hide_price') or x.get('hide_price_on_site')
        if hidden:
            flags.append('сайт скрывает цену')
        r.add(lot_id=x.get('number'), lot_name='Офис', area=num(x.get('area')), floor=x.get('floor_number'),
              status='В продаже', price_total=None if hidden else num(x.get('price')), price_m2=num(x.get('ppm')) or None,
              url=t['url'], flags='; '.join(flags) or None)
    expected = sum(f['total_count'] for f in floors)
    if expected != len(r.lots):
        r.notes.append(f'по этажам заявлено {expected}, взято {len(r.lots)}')
    return r
