"""Hydra-вариант для коммерции (upside-ostankino.ru): GET /api/hydra/data/commerce.
Поля: b корпус, f этаж, tn номер, sq площадь, tc цена лота, cpm цена за м², st статус (1 = доступно).
Корпус, который продаётся целиком, на сайте задан не лотами, а строкой «площадь здания × ₽/м²» в тексте страницы."""
import re
from core import get, num, Result

_cache = {}


def _data(t):
    if t['url'] not in _cache:
        _cache[t['url']] = get(t['url'], timeout=40, headers={'Accept': 'application/json'}).json()
    return _cache[t['url']]


def _whole_building(t, r):
    html = get(t['page']).text
    text = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', re.sub(r'<script.*?</script>|<style.*?</style>', '', html, flags=re.S)))
    m = re.search(r'КОРПУС\s*%s\s+Стоимость за м²\s*([\d\s]+)₽\s*Общая площадь\s*([\d\s]+)м²' % t['hc_whole'], text, re.I)
    if not m:
        r.error = 'не найден блок «Корпус %s» на странице (вёрстка изменилась?)' % t['hc_whole']
        return
    m2, area = num(m.group(1)), num(m.group(2))
    r.add(lot_id=f'Корпус {t["hc_whole"]} целиком', lot_name='Здание целиком', area=area, status='В продаже',
          price_total=round(m2 * area) if m2 and area else None, price_m2=m2, url=t['page'],
          flags='цена посчитана: площадь × ₽/м² (сайт показывает только ₽/м²)')


def run(t):
    r = Result(t)
    try:
        if t.get('hc_whole'):
            _whole_building(t, r)
            return r
        d = _data(t)
    except Exception as e:                           # noqa: BLE001
        r.error = str(e)
        return r
    other = {}
    for v in d.get('apartments', {}).values():
        if str(v.get('b')) != str(t['hc_building']):
            continue
        if v.get('st') != 1:
            other[v.get('st')] = other.get(v.get('st'), 0) + 1
            continue
        r.add(lot_id=v.get('tn'), lot_name='Офис', area=v.get('sq'), floor=v.get('f'), status='В продаже',
              price_total=v.get('tc'), price_m2=round(v['cpm']) if v.get('cpm') else None, url=t['page'])
    if other:
        r.notes.append('не в продаже (код статуса: шт.): ' + ', '.join(f'{k}: {n}' for k, n in sorted(other.items(), key=str)))
    return r
