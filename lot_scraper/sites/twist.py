"""twist-office.ru: GET /local/ajax/flats/?filter=... (JSON, без куки). real_price — с НДС (поле vat это подтверждает)."""
import json
from urllib.parse import quote
from core import get, num, Result


def run(t):
    r = Result(t)
    try:
        q = quote(json.dumps({'hide_sold': ['Y'], 'hide_reserved': ['Y']}, separators=(',', ':')))
        d = get(f'https://twist-office.ru/local/ajax/flats/?filter={q}', timeout=40, headers={'Accept': 'application/json'}).json()
    except Exception as e:                           # noqa: BLE001
        r.error = str(e)
        return r
    for x in d.get('data', []):
        if x.get('sold'):
            continue
        r.add(lot_id=x.get('num'), lot_name=x.get('type') or 'Офис', area=num(x.get('sq')), floor=num(x.get('floor')),
              finish=x.get('finishing') or None, status='В продаже', price_total=num(x.get('real_price')), url=t['url'])
    if d.get('count') is not None and d['count'] != len(d.get('data', [])):
        r.notes.append(f"сайт заявил {d['count']}, получено {len(d.get('data', []))}")
    return r
