"""Виджет Profitbase на сайте застройщика (pbNNNN.profitbase.ru): токен выдаётся любому посетителю сайта
(POST /api/v4/json/authentication с referrer сайта), затем GET /api/v4/json/property?houseId=... Дом = корпус.
Параметры цели: pb_domain, pb_referer, pb_house. price.value — цена, которую показывает виджет; prevValue — до скидки."""
import time, requests
from core import HEAD, num, Result

_tok = {}
PAGE = 100


def _token(domain, referer):
    k = (domain, referer)
    if k not in _tok:
        r = requests.post(f'https://{domain}/api/v4/json/authentication', headers={**HEAD, 'Accept': 'application/json'},
                          json={'type': 'external-site-widget', 'credentials': {'referrer': referer, 'referer': referer}}, timeout=30)
        r.raise_for_status()
        _tok[k] = r.json()['access_token']
    return _tok[k]


def _props(domain, referer, house):
    out, offset, total = [], 0, None
    while True:
        params = {'houseId': house, 'status[0]': 'AVAILABLE', 'returnFilteredCount': 'true', 'limit': PAGE, 'offset': offset,
                  'access_token': _token(domain, referer)}
        last = None
        for i in range(3):
            try:
                r = requests.get(f'https://{domain}/api/v4/json/property', params=params, headers={**HEAD, 'Accept': 'application/json'}, timeout=40)
                if r.status_code == 200:
                    d = r.json()['data']
                    break
                last = f'HTTP {r.status_code}'
            except Exception as e:                       # noqa: BLE001
                last = type(e).__name__
            time.sleep(1.5 * (i + 1))
        else:
            raise RuntimeError(f'{domain} house {house}: {last}')
        rows = d.get('properties', [])
        total = d.get('filteredCount', total)
        new = [x for x in rows if x['id'] not in {y['id'] for y in out}]
        out += new
        offset += PAGE
        if not new or len(rows) < PAGE or (total is not None and len(out) >= total):
            return out, total


def run(t):
    r = Result(t)
    try:
        rows, total = _props(t['pb_domain'], t['pb_referer'], t['pb_house'])
    except Exception as e:                           # noqa: BLE001
        r.error = str(e)
        return r
    for x in rows:
        if x.get('status') != 'AVAILABLE' or x.get('propertyType') not in (None, 'office', 'commercial'):
            continue
        pr = x.get('price') or {}
        flags = []
        if pr.get('prevValue') and pr.get('value') and pr['prevValue'] != pr['value']:
            flags.append(f"цена до скидки {pr['prevValue']:,.0f} ₽".replace(',', ' '))
        r.add(lot_id=x.get('number'), lot_name='Офис', area=num((x.get('area') or {}).get('area_total')), floor=num(x.get('floor')),
              finish=x.get('facing'), status='В продаже', price_total=num(pr.get('value')), price_m2=num(pr.get('pricePerMeter')),
              url=t['url'], flags='; '.join(flags) or None)
    if total is not None and total != len(rows):
        r.notes.append(f'сайт заявил {total}, получено {len(rows)}')
    return r
