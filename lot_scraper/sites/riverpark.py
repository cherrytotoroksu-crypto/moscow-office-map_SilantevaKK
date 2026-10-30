"""river-park.ru: GET /ajax/flats/ (JSON, все лоты за один запрос). Берём «апартаменты» нужного корпуса,
жилые «Квартира» (корпус 4) отбрасываем. reserved=Y пропускаем."""
from core import get, num, Result

API = ('https://river-park.ru/ajax/flats/?page=1&cnt=500&filter%5Bproject%5D=Riverpark&filter%5Bspecial%5D='
       '&filter%5Btype%5D=&filter%5Bbld%5D=&filter%5Boffers%5D=&filter%5Bfinishing%5D=0&sort%5Bsec%5D=0'
       '&sort%5Bname%5D=0&sort%5Bsq%5D=0&sort%5Bprice%5D=1&sort%5Brooms%5D=0&sort%5Bfloor%5D=0&art_code=flat')
_cache = {}


def run(t):
    r = Result(t)
    try:
        if 'd' not in _cache:
            _cache['d'] = get(API, timeout=60).json()
        d = _cache['d']
    except Exception as e:
        r.error = str(e)
        return r
    skipped_res = skipped_apt = 0
    for x in d.get('data', []):
        if str(x.get('building')) != str(t['river_building']):
            continue
        if x.get('articlesubtype') != 'апартаменты':
            skipped_apt += 1
            continue
        if x.get('reserved') == 'Y':
            skipped_res += 1
            continue
        r.add(lot_id=x.get('lotcode') or x.get('num'), lot_name=f"Корпус {x['building']}, секция {x['section']}",
              area=num(x.get('sq')), floor=num(x.get('floor')), status='В продаже',
              price_total=num(x.get('real_price')), price_m2=num(x.get('real_meterprice')),
              url='https://river-park.ru/lots/scheme/%s/%s/%s/%s/' % (x['building'], x['section'], x['floor'], x['num']))
    if d.get('count') is not None and len(d.get('data', [])) != d['count']:
        r.notes.append(f"сайт заявил {d['count']}, получено {len(d.get('data', []))}")
    if skipped_res:
        r.notes.append(f'бронь, не взято: {skipped_res}')
    if skipped_apt:
        r.notes.append(f'не апартаменты, не взято: {skipped_apt}')
    return r
