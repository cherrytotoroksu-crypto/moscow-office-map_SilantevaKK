"""Автодетектор лотов: в произвольном JSON (ответ API, __NEXT_DATA__, встроенный в HTML JSON) находит массивы объектов,
похожие на лоты (есть площадь и цена/этаж), и сопоставляет их поля со схемой core.FIELDS по названию и значениям.
Ничего не знает о конкретном сайте: используется и офлайн (по снимкам recon), и онлайн (по ответам страницы в браузере)."""
import re, json

AREA = re.compile(r'(^|_)(area|square|sq|sqm|plosh\w*|s_?total|total_?area|actual_?area|area_?total|areatotal|size)(_|$)', re.I)
PRICE = re.compile(r'(price|cost|stoim\w*|summ?a?|total_?price|full_?price)', re.I)
PRICE_M2 = re.compile(r'(price_?m2|price_?per|ppm|meter_?(price|cost)|cost_?m2|price_?sqm|per_?m)', re.I)
PRICE_OLD = re.compile(r'(old|base|before|start|origin|без_?скид)', re.I)
FLOOR = re.compile(r'(^|_)(floor|etazh|level|storey)(_?number|_?num|_?no)?($|_)', re.I)
ID = re.compile(r'(^|_)(number|num|no|article|lot_?id|flat_?id|id|name|title|code)($|_)', re.I)
STATUS = re.compile(r'(status|state|sold|booked|reserv|available|is_?free)', re.I)
SKIP_KEYS = re.compile(r'(coord|lat|lng|lon|phone|zip|year|quarter|count|rooms|percent|rate|discount_?p)', re.I)


def _num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        t = re.sub(r'[^\d,.\-]', '', v.replace('\xa0', '').replace(' ', '')).replace(',', '.')
        if t.count('.') > 1:
            t = t.replace('.', '', t.count('.') - 1)
        try:
            return float(t) if t not in ('', '.', '-') else None
        except ValueError:
            return None
    if isinstance(v, dict):                                   # {"value": 12.3} / {"area": 12.3}
        for k in ('value', 'val', 'amount', 'total', 'area'):
            if k in v:
                return _num(v[k])
    return None


def _flat(d, prefix='', depth=0):
    """Плоский вид объекта: вложенные словари разворачиваются до глубины 2 (layout.area -> layout_area)."""
    out = {}
    for k, v in d.items():
        key = f'{prefix}{k}'
        if isinstance(v, dict) and depth < 2 and len(v) <= 40:
            out.update(_flat(v, key + '_', depth + 1))
            out.setdefault(key, v)
        else:
            out[key] = v
    return out


def _walk(o, path='$', depth=0):
    if depth > 9:
        return
    if isinstance(o, list):
        if len(o) >= 2 and sum(isinstance(x, dict) for x in o) >= 0.9 * len(o):
            yield path, o
        for i, x in enumerate(o[:50]):
            yield from _walk(x, f'{path}[]', depth + 1)
    elif isinstance(o, dict):
        for k, v in o.items():
            yield from _walk(v, f'{path}.{k}', depth + 1)
    elif isinstance(o, str) and len(o) > 200 and o[:1] in '[{' and depth < 3:     # JSON внутри строки
        try:
            yield from _walk(json.loads(o), path + '(json)', depth + 1)
        except ValueError:
            pass


def _pick(keys_vals, rx, lo, hi, exclude=None):
    """Лучшее поле по имени + правдоподобному диапазону значений (по медиане)."""
    best = None
    for k, vals in keys_vals.items():
        if SKIP_KEYS.search(k) and not rx.search(k):
            continue
        if not rx.search(k) or (exclude and exclude.search(k)):
            continue
        nums = sorted(n for n in (_num(v) for v in vals) if n is not None)
        if len(nums) < 0.6 * len(vals):
            continue
        med = nums[len(nums) // 2]
        if not lo <= med <= hi:
            continue
        score = len(nums) / len(vals) + (0.3 if k.lower() in ('area', 'price', 'floor') else 0) - 0.02 * k.count('_')
        if not best or score > best[0]:
            best = (score, k)
    return best[1] if best else None


def analyse(arr):
    """Схема массива: какие поля соответствуют площади/цене/этажу/номеру/статусу; None, если не похоже на лоты."""
    rows = [_flat(x) for x in arr[:400] if isinstance(x, dict)]
    if len(rows) < 2:
        return None
    kv = {}
    for r in rows:
        for k, v in r.items():
            kv.setdefault(k, []).append(v)
    kv = {k: v for k, v in kv.items() if len(v) >= 0.6 * len(rows)}
    area = _pick(kv, AREA, 3, 20000)
    price_m2 = _pick(kv, PRICE_M2, 20000, 3_000_000)
    price = _pick(kv, PRICE, 300_000, 5_000_000_000, exclude=re.compile(PRICE_OLD.pattern + '|' + PRICE_M2.pattern, re.I))
    floor = _pick(kv, FLOOR, -5, 150)
    if not area or not (price or price_m2):
        return None
    ident = None
    for k in kv:
        if ID.search(k) and not SKIP_KEYS.search(k):
            vals = [r.get(k) for r in rows]
            if all(isinstance(v, (str, int)) for v in vals if v is not None) and len({str(v) for v in vals}) > 0.8 * len(vals):
                ident = k
                if re.search(r'number|num|article|lot', k, re.I):
                    break
    status = next((k for k in kv if STATUS.search(k)), None)
    old = _pick(kv, re.compile(r'price|cost', re.I), 300_000, 5_000_000_000, exclude=PRICE_M2)
    return dict(n=len(arr), area=area, price=price, price_m2=price_m2, floor=floor, id=ident, status=status,
                score=len(arr) * (1 + (price is not None) + (floor is not None) + (ident is not None)))


def find_lot_arrays(obj):
    """Все правдоподобные массивы лотов в объекте: [(путь, массив, схема)], лучшие первыми."""
    res = []
    for path, arr in _walk(obj):
        sch = analyse(arr)
        if sch:
            res.append((path, arr, sch))
    res.sort(key=lambda x: -x[2]['score'])
    return res


def json_blobs(html):
    """JSON, встроенный в HTML: __NEXT_DATA__, window.__X__ = {...}, <script type=application/json|ld+json>."""
    out = []
    for m in re.finditer(r'<script[^>]*(?:type="application/(?:json|ld\+json)"|id="__NEXT_DATA__")[^>]*>(.*?)</script>', html, re.S):
        try:
            out.append(json.loads(m.group(1)))
        except ValueError:
            pass
    for m in re.finditer(r'(?:window\.[\w$]+|var\s+\w+|const\s+\w+)\s*=\s*([\[{].{200,}?[\]}])\s*;?\s*</script>', html, re.S):
        try:
            out.append(json.loads(m.group(1)))
        except ValueError:
            pass
    return out


def to_lots(arr, sch):
    """Сопоставление строк массива полям core.FIELDS. Возвращает список dict для Result.add()."""
    lots = []
    for x in arr:
        if not isinstance(x, dict):
            continue
        f = _flat(x)
        lots.append(dict(lot_id=f.get(sch['id']) if sch['id'] else None, area=_num(f.get(sch['area'])),
                         floor=_num(f.get(sch['floor'])) if sch['floor'] else None,
                         price_total=_num(f.get(sch['price'])) if sch['price'] else None,
                         price_m2=_num(f.get(sch['price_m2'])) if sch['price_m2'] else None,
                         _status=f.get(sch['status']) if sch['status'] else None))
    return lots
