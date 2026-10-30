"""donstroy.moscow (БП Раменки): POST JSON API, куки не нужны (проверено 30.10.2026)."""
import requests
from core import HEAD, Result

API = 'https://donstroy.moscow/api/v1/offices/choose_params_api_flats/'


def run(t):
    r = Result(t)
    body = {"price": [], "area": [], "floor_number": [], "projects": [t['donstroy_project']],
            "quarters": [], "buildings": [], "sort": "price-asc"}
    head = {**HEAD, 'Content-Type': 'application/json', 'Origin': 'https://donstroy.moscow',
            'Referer': 'https://donstroy.moscow/offices/'}
    lots, total = [], None
    try:
        for page in range(1, 30):
            d = requests.post(API, json={**body, 'page': page}, headers=head, timeout=30).json()
            total = d.get('total_flats', 0)
            if not d.get('flats'):
                break
            lots += d['flats']
            if len(lots) >= total:
                break
    except Exception as e:
        r.error = f'{type(e).__name__}: {str(e)[:80]}'
        return r
    for f in lots:
        flags = []
        if f.get('price_request'):
            flags.append('цена по запросу')
        if f.get('price_old'):
            flags.append(f"старая цена {f['price_old']}")
        fin = {'0': 'Без отделки', '1': 'Отделка', '2': 'С мебелью'}.get(str(f.get('furnish')))
        r.add(lot_id=str(f.get('title', '')).strip() or str(f.get('number')), lot_name=f.get('title'),
              area=float(f['area']) if f.get('area') else None,
              floor=f.get('floor'), finish=fin, status='В продаже',
              price_total=None if f.get('price_request') else f.get('price'),
              url='https://donstroy.moscow' + f.get('link', ''), flags='; '.join(flags) or None)
    if total is not None and total != len(lots):
        r.notes.append(f'сайт заявил {total}, получено {len(lots)}')
    return r
