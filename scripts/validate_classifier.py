"""
QA-011 (minimal version) — блокирующие проверки classifier.html.

Запуск: python3 scripts/validate_classifier.py
Печатает найденные проблемы и завершается с кодом 1, если есть хотя бы одна.
Не покрывает всё, что просил Codex в QA-011 (полный генератор classifier.html
из канонических JSON) — это отдельная, более крупная работа. Здесь — только
дешёвые структурные проверки, которые ловят уже дважды случившиеся в этом
проекте классы багов.

Проверки:
1. RAW_DATA и COLORMAP парсятся как валидный JSON.
2. Внутри одного цветового блока (green/yellow/red) нет повторяющихся ключей
   (иначе JS тихо теряет более раннюю запись — см. историю проекта, баг был
   пойман руками минимум дважды).
3. Известные координаты-заглушки (места, где раньше были обнаружены баги
   геокодирования) отсутствуют в текущих данных.
4. Записи COLORMAP, чьё имя соответствует НЕСКОЛЬКИМ строкам RAW_DATA с
   разными lat/lng или address — предупреждение (не ошибка): цвет по имени
   может неправильно покрасить чужую строку. Список таких имён печатается,
   решение — за человеком/агентом (объединять, разносить по стабильному ID
   или явно игнорировать).
5. Геополя (ao/raion/zone/submarket/bizFormed/bizForming) каждой строки
   RAW_DATA пересчитываются через recompute_geo.py и сверяются с тем, что
   реально хранится — расхождения печатаются как предупреждения.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from recompute_geo import compute_geo

CLASSIFIER_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "classifier.html")

KNOWN_PLACEHOLDER_COORDS = [
    (55.755819, 37.617644),  # mega-cluster placeholder found 2026-07-26/27
]

GEO_FIELDS = ["ao", "raion", "zone", "submarket", "bizFormed", "bizForming"]


def extract_balanced(html, name, open_ch, close_ch):
    idx = html.index("const " + name)
    start = html.index(open_ch, idx)
    depth = 0
    in_str = False
    str_ch = ""
    esc = False
    for i in range(start, len(html)):
        c = html[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == str_ch:
                in_str = False
        else:
            if c in ('"', "'", "`"):
                in_str = True
                str_ch = c
            elif c == open_ch:
                depth += 1
            elif c == close_ch:
                depth -= 1
                if depth == 0:
                    return html[start:i + 1]
    raise ValueError(f"unbalanced {name}")


def find_duplicate_keys_in_block(html, block_name):
    """Regex-free duplicate-key scan for a top-level JS object block by counting
    `"key":` occurrences at the correct nesting depth within COLORMAP.<block_name>."""
    colormap_text = extract_balanced(html, "COLORMAP", "{", "}")
    marker = f'"{block_name}": {{'
    start = colormap_text.index(marker) + len(marker)
    depth = 1
    in_str = False
    str_ch = ""
    esc = False
    keys = []
    i = start
    current_key = None
    expect_key = True
    while depth > 0:
        c = colormap_text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == str_ch:
                in_str = False
                if expect_key and depth == 1:
                    keys.append(current_key)
            else:
                if expect_key:
                    current_key = (current_key or "") + c
        else:
            if c in ('"', "'"):
                in_str = True
                str_ch = c
                if expect_key:
                    current_key = ""
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            elif c == "[" and depth == 1:
                expect_key = False
            elif c == "]" and depth == 1:
                expect_key = True
        i += 1
    seen = {}
    dupes = []
    for k in keys:
        seen[k] = seen.get(k, 0) + 1
    for k, n in seen.items():
        if n > 1:
            dupes.append((k, n))
    return dupes


def main():
    problems = []
    warnings = []

    with open(CLASSIFIER_PATH, encoding="utf-8") as f:
        html = f.read()

    # 1. JSON validity
    try:
        raw_data_text = extract_balanced(html, "RAW_DATA", "[", "]")
        raw_data = json.loads(raw_data_text)
    except Exception as e:
        problems.append(f"RAW_DATA does not parse as JSON: {e}")
        raw_data = []

    try:
        colormap_text = extract_balanced(html, "COLORMAP", "{", "}")
        colormap = json.loads(colormap_text)
    except Exception as e:
        problems.append(f"COLORMAP does not parse as JSON: {e}")
        colormap = {"green": {}, "yellow": {}, "red": {}}

    # 2. Duplicate keys within a color block
    for block in ("green", "yellow", "red"):
        dupes = find_duplicate_keys_in_block(html, block)
        for key, n in dupes:
            problems.append(f"COLORMAP.{block} has duplicate key {key!r} ({n} occurrences) — earlier entry is silently lost by JS")

    # 3. Known placeholder coordinates
    for rec in raw_data:
        lat, lng = rec.get("lat"), rec.get("lng")
        for plat, plng in KNOWN_PLACEHOLDER_COORDS:
            if lat == plat and lng == plng:
                problems.append(f"{rec.get('name')!r} still on known placeholder coordinate ({plat},{plng})")

    # 4. Name collisions: same combined name, different lat/lng or address
    by_name = {}
    for rec in raw_data:
        by_name.setdefault(rec.get("name"), []).append(rec)
    for name, recs in by_name.items():
        if len(recs) < 2:
            continue
        coords = {(r.get("lat"), r.get("lng")) for r in recs}
        addrs = {r.get("address") for r in recs}
        if len(coords) > 1 or len(addrs) > 1:
            warnings.append(f"{name!r}: {len(recs)} rows share this display name but differ in lat/lng or address — a COLORMAP entry for this name colors ALL of them")

    # 5. Geo-field drift (only for rows with a real lat/lng)
    for rec in raw_data:
        lat, lng = rec.get("lat"), rec.get("lng")
        if lat is None or lng is None:
            continue
        computed = compute_geo(lat, lng)
        mismatches = []
        for field in GEO_FIELDS:
            stored = rec.get(field) or ""
            expect = computed.get(field) or ""
            if stored != expect:
                mismatches.append(f"{field}: stored={stored!r} expected={expect!r}")
        if mismatches:
            warnings.append(f"{rec.get('name')!r} geo drift: " + "; ".join(mismatches))

    print(f"=== RAW_DATA rows: {len(raw_data)} ===")
    print(f"=== PROBLEMS (blocking): {len(problems)} ===")
    for p in problems:
        print("  ERROR:", p)
    print(f"=== WARNINGS (non-blocking): {len(warnings)} ===")
    for w in warnings:
        print("  WARN:", w)

    if problems:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
