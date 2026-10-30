"""chalet40.moscow: сайт тянет лоты из опубликованной Google-таблицы застройщика (CSV)."""
import csv, io, re
from core import get, num, Result

CSV = ('https://docs.google.com/spreadsheets/d/e/2PACX-1vTPJicFqzKPT_ljQtpSpxeaJ6zXiZ2rsX8waONHH7sg6XbqgupKb4zBHoS95OYMybW6LGlgYSUAuRGg'
       '/pub?gid=1216103885&single=true&output=csv')


def run(t):
    r = Result(t)
    try:
        rows = list(csv.DictReader(io.StringIO(get(CSV).content.decode('utf-8'))))
    except Exception as e:
        r.error = str(e)
        return r
    other = {}
    for x in rows:
        if x.get('section') != t['chalet_section']:
            continue
        if x.get('type') != 'room':
            other['тип ' + str(x.get('type'))] = other.get('тип ' + str(x.get('type')), 0) + 1
            continue
        if x.get('status') != 'available':
            other[x.get('status')] = other.get(x.get('status'), 0) + 1
            continue
        vat = 'включая НДС' in (x.get('total-ru') or '')
        r.add(lot_id=x.get('name'), lot_name=x.get('name-ru'), area=num(re.sub(r'м.*', '', x.get('square') or '')),
              floor=num(x.get('floor')), status='В продаже',
              price_total=num(re.sub(r'р\..*', '', x.get('total-ru') or '')),
              price_m2=num(re.sub(r'р\..*', '', x.get('kv-ru') or '')), url=t['url'],
              flags=None if vat else 'НДС в цене не подтверждён')
    if other:
        r.notes.append('не взято: ' + ', '.join(f'{k}: {v}' for k, v in other.items()))
    return r
