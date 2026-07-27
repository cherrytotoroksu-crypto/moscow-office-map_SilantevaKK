"""
QA-008 — детерминированный пересчёт геополей (АО/район/зона/субрынок/деловые районы)
по координатам, той же логикой point-in-polygon, что использует index.html
(ray-casting с bbox pre-check, см. index.html: pipRing/pointInFeature).

Использование:
    from recompute_geo import compute_geo
    compute_geo(lat, lng) -> {"ao":..., "raion":..., "zone":..., "submarket":...,
                              "bizFormed":..., "bizForming":...}

Валидировано (2026-07-27): 0 расхождений на 20 случайных уже проверенных
записях classifier.html с непустыми geo-полями.

Соответствие слоёв (см. index.html LAYER_CFG):
  ao         -> data/ao.geojson         (свойство NAME_AO)
  raion      -> data/mo.geojson         (свойство NAME)
  zone       -> data/zones.geojson      (свойство name, код латиницей -> ZONE_NAMES)
  submarket  -> data/submarkets.geojson (свойство name)
  bizFormed  -> data/biz_formed.geojson (свойство name)
  bizForming -> data/biz_forming.geojson(свойство district)

ВАЖНО: zone использует ОБЫЧНЫЙ дефис (ТТК-МКАД), а не en-dash, как в
ZONE_NAMES внутри index.html (там ТТК–МКАД с длинным тире) — это
исторически два независимых написания в двух разных частях проекта;
здесь сохранена конвенция classifier.html, т.к. её пришлось проверять
построчно против уже существующих (верных) записей.
"""
import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

ZONE_NAMES = {
    'BR': 'Центральное ядро (БК)',
    'BR-GR': 'БК-СК',
    'GR-TTR': 'СК-ТТК',
    'TTR-MKAD': 'ТТК-МКАД',
    'ZA-MKAD': 'за МКАД',
}

LAYERS = {
    'ao':         ('ao.geojson', 'NAME_AO', None),
    'raion':      ('mo.geojson', 'NAME', None),
    'zone':       ('zones.geojson', 'name', ZONE_NAMES),
    'submarket':  ('submarkets.geojson', 'name', None),
    'bizFormed':  ('biz_formed.geojson', 'name', None),
    'bizForming': ('biz_forming.geojson', 'district', None),
}

_cache = {}


def _load_layer(key):
    if key in _cache:
        return _cache[key]
    fname, field, mapping = LAYERS[key]
    with open(os.path.join(DATA_DIR, fname), encoding="utf-8") as fh:
        gj = json.load(fh)
    feats = []
    for f in gj["features"]:
        geom = f["geometry"]
        polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"] if geom["type"] == "MultiPolygon" else []
        minx = miny = float("inf")
        maxx = maxy = float("-inf")
        for poly in polys:
            for ring in poly:
                for x, y in ring:
                    if x < minx: minx = x
                    if x > maxx: maxx = x
                    if y < miny: miny = y
                    if y > maxy: maxy = y
        name = f["properties"].get(field)
        if mapping:
            name = mapping.get(name, name)
        feats.append((minx, miny, maxx, maxy, polys, name))
    _cache[key] = feats
    return feats


def _pip_ring(ring, x, y):
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _point_in_feature(lng, lat, minx, miny, maxx, maxy, polys):
    if lng < minx or lng > maxx or lat < miny or lat > maxy:
        return False
    for poly in polys:
        if not _pip_ring(poly[0], lng, lat):
            continue
        in_hole = False
        for h in range(1, len(poly)):
            if _pip_ring(poly[h], lng, lat):
                in_hole = True
                break
        if not in_hole:
            return True
    return False


def compute_geo(lat, lng):
    """Возвращает dict {ao, raion, zone, submarket, bizFormed, bizForming} для точки.
    Пустая строка означает «точка не попала ни в один полигон слоя» (это НЕ ошибка —
    для некоторых слоёв, например деловых районов, это нормальное состояние)."""
    result = {}
    for key in LAYERS:
        feats = _load_layer(key)
        found = ""
        for minx, miny, maxx, maxy, polys, name in feats:
            if _point_in_feature(lng, lat, minx, miny, maxx, maxy, polys):
                found = name
                break
        result[key] = found
    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 3:
        lat, lng = float(sys.argv[1]), float(sys.argv[2])
        print(json.dumps(compute_geo(lat, lng), ensure_ascii=False, indent=2))
    else:
        print("Usage: python3 recompute_geo.py <lat> <lng>")
