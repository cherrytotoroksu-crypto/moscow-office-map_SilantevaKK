"""Платформа Hydra (opus-bc.ru, kobzon.city и др.): один JSON /api/hydra/data.
Поля лота: b корпус, f этаж, n номер, tr_n номер для клиента, sq площадь, st статус,
cpm цена за м², tc цена лота, tcd цена со скидкой, t тип помещения."""
from core import get, Result


def run(t):
    r = Result(t)
    try:
        d = get(t['url']).json()
    except Exception as e:
        r.error = str(e)
        return r
    free = t.get('free_status', 1)
    other = {}
    for key, v in d.get('apartments', {}).items():
        typ = str(v.get('t') or '')
        if 'офис' not in typ.lower() or v.get('isR') or v.get('isOffice') is False:
            continue
        if t.get('building') and str(v.get('b')) != str(t['building']):
            continue
        if v.get('st') != free:
            other[v.get('st')] = other.get(v.get('st'), 0) + 1
            continue
        flags = []
        if v.get('tcd') and v['tcd'] != v.get('tc'):
            flags.append(f"есть цена со скидкой {v['tcd']}")
        r.add(lot_id=str(v.get('tr_n') or v.get('n')), lot_name=typ, area=v.get('sq'), floor=v.get('f'),
              finish=typ, status='В продаже', price_total=v.get('tc'), price_m2=v.get('cpm'),
              url=t.get('page', t['url']), flags='; '.join(flags) or None)
    if other:
        r.notes.append('не в продаже (код статуса: шт.): ' + ', '.join(f'{k}: {n}' for k, n in sorted(other.items(), key=str)))
    return r
