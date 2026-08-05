# -*- coding: utf-8 -*-
"""Экспорт листа «Все объекты (чистый)» из свода будущих проектов в JSON для слоя карты.

Источник: Будущие_проекты_очищено_с_памятью.xlsx (подготовлен Codex, 2026-08-05).
Лист «Все объекты (чистый)» — единственный источник геометрии (см. промпт на листе
«Промпт для Клода»). Объекты без полной пары координат в geometry НЕ попадают —
они выносятся в отдельный список no_coords, без геокодинга по догадке.
"""
import json
import re
import sys
from pathlib import Path

import openpyxl

SRC = Path(r'C:\Users\zapas\Documents\Codex\2026-08-05\final-2-xlsx\outputs\Будущие_проекты_очищено_с_памятью.xlsx')
REPO = Path(__file__).resolve().parent.parent
OUT = REPO / 'data' / 'future_projects.json'

SHEET = 'Все объекты (чистый)'

FIELD_MAP = {
    'ID': 'id',
    'Объект': 'name',
    'Адрес': 'address',
    'Девелопер': 'developer',
    'Площадь общая': 'gba',
    'GLA': 'gla',
    'Класс': 'cls',
    'Квартал ввода': 'commission_quarter',
    'Год ввода': 'commission_year',
    'Статус': 'status',
    'Широта': 'lat',
    'Долгота': 'lng',
    'Статус проверки': 'verification_status',
    'Уровень доверия': 'confidence',
    'Интернет-источники': 'sources',
    'Конфликты': 'conflicts',
    'Число дублей': 'merged_rows',
    'Исходные вкладки': 'source_sheets',
}


# Точечные исправления координат в исходном своде. Только случаи, где ошибка
# механическая и восстановление проверяемо внешним источником — не подбор
# «правдоподобной» точки. Каждая запись обязана иметь источник.
COORD_FIXES = {
    # Долгота 7.667015 — обрезана первая цифра (точка уезжала в Германию).
    # Восстановленная 37.667015 попадает на пр-т Андропова примерно в 600 м
    # от парка «Остров Мечты» (2ГИС даёт для самого парка 55.694483,
    # 37.676309, https://2gis.ru/moscow/firm/70000001041928194) — для ТПУ
    # у того же проспекта это согласуется. Широта в исходнике верная.
    'OBJ-0464': {
        'lng': 37.667015,
        'source': 'восстановлена отрезанная цифра долготы; сверено с 2ГИС по пр-т Андропова, 1',
    },
}


def to_float(v):
    if v is None or v == '':
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return None


def to_int(v):
    f = to_float(v)
    return int(f) if f is not None else None


def split_sources(v):
    if not v:
        return []
    return [u.strip() for u in re.split(r'[;\n]+', str(v)) if u.strip()]


def main():
    wb = openpyxl.load_workbook(SRC, data_only=True, read_only=True)
    ws = wb[SHEET]
    rows = ws.iter_rows(values_only=True)
    header = [h for h in next(rows)]
    idx = {h: i for i, h in enumerate(header) if h}

    records = []
    no_coords = []
    for row in rows:
        if not row or not row[idx['ID']]:
            continue
        rec = {}
        for col, key in FIELD_MAP.items():
            i = idx.get(col)
            rec[key] = row[i] if i is not None and i < len(row) else None

        rec['lat'] = to_float(rec['lat'])
        rec['lng'] = to_float(rec['lng'])
        rec['gba'] = to_float(rec['gba'])
        rec['gla'] = to_float(rec['gla'])
        rec['commission_year'] = to_int(rec['commission_year'])
        rec['commission_quarter'] = to_int(rec['commission_quarter'])
        rec['merged_rows'] = to_int(rec['merged_rows'])
        rec['sources'] = split_sources(rec['sources'])

        fix = COORD_FIXES.get(rec['id'])
        if fix:
            for key in ('lat', 'lng'):
                if key in fix:
                    rec[key + '_raw'] = rec[key]
                    rec[key] = fix[key]
            rec['coord_fix_source'] = fix['source']

        if rec['lat'] is None or rec['lng'] is None:
            no_coords.append(rec)
        else:
            records.append(rec)

    payload = {
        'source_file': SRC.name,
        'source_sheet': SHEET,
        'generated_by': 'scripts/export_future_projects.py',
        'total': len(records) + len(no_coords),
        'with_coords': len(records),
        'without_coords': len(no_coords),
        'projects': records,
        'no_coords': no_coords,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open('w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    # сводка в stdout-friendly файл (кириллица в консоли Windows не печатается)
    stats = {
        'total': payload['total'],
        'with_coords': payload['with_coords'],
        'without_coords': payload['without_coords'],
        'by_status': {},
        'by_confidence': {},
    }
    for r in records + no_coords:
        stats['by_status'][r['status'] or '—'] = stats['by_status'].get(r['status'] or '—', 0) + 1
        stats['by_confidence'][r['confidence'] or '—'] = stats['by_confidence'].get(r['confidence'] or '—', 0) + 1

    stats_path = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT.with_name('future_projects_stats.json')
    with stats_path.open('w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
