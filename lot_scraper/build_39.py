"""Сырая выгрузка (out/lots_raw_*.xlsx) -> таблица в 39 колонок по памятке office-lot-workbooks + сверка с Q3.
Метаданные корпуса (ID, девелопер, класс, адрес, площади, гео) берутся из свода Q3 2026 (последняя версия).
Фаза проекта и схема продажи НЕ заполняются (проверяются отдельно); НДС-колонки считаются формулой от схемы.
Запуск: python build_39.py [сырой_файл.xlsx]"""
import sys, glob, os, json, datetime, collections, csv, re
from pathlib import Path
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

HERE = Path(__file__).resolve().parent


def svod_path():
    """Свод с метаданными корпусов: config.json {"svod": "путь"} либо самый свежий «Свод Q3 2026_итоговый_*.xlsx» в ../../Q3 2026."""
    cfg = HERE / 'config.json'
    if cfg.exists():
        p = json.loads(cfg.read_text(encoding='utf-8')).get('svod')
        if p and Path(p).exists():
            return p
    found = sorted(glob.glob(str(HERE.parent.parent / 'Q3 2026' / 'Свод Q3 2026_итоговый_*.xlsx')), key=os.path.getmtime)
    if not found:
        raise FileNotFoundError('Не найден свод Q3 2026. Укажи путь в lot_scraper/config.json: {"svod": "C:/.../Свод.xlsx"}')
    return found[-1]
COLS = ['ID проекта', 'SubID корпуса', 'ID лота', 'Девелопер', 'Название проекта', 'Название корпуса',
        'Здание/блок', 'Класс', 'Адрес', 'Квартал ввода', 'Год ввода', 'Введен / не введен', 'Фаза проекта',
        'Общая площадь проекта', 'Площадь офисов проекта', 'Общая площадь корпуса', 'Площадь офисов корпуса',
        'Статус', 'Площадь лота', 'Этаж', 'Отделка', 'Схема продажи', 'Цена лота без НДС',
        'Цена лота руб./кв.м безНДС', 'Вес', 'Стоимость лота с НДС', 'НДС', 'Округ', 'Район', 'Зона', 'Субрынок',
        'Широта', 'Долгота', 'Дата', 'Ссылка1', 'Ссылка 2', 'Ссылка 3', 'Ссылка 4', 'Ссылка']
assert len(COLS) == 39
IDX = {c: i + 1 for i, c in enumerate(COLS)}


def raw_path():
    if len(sys.argv) > 1:
        return sys.argv[1]
    return sorted(glob.glob(str(HERE / 'out' / 'lots_raw_*.xlsx')), key=os.path.getmtime)[-1]


def finish_label(v):
    t = (v or '').lower()
    if not t:
        return None
    if 'без отделки' in t:
        return 'Без отделки'
    if 'предчист' in t or 'white' in t or 'белый' in t:
        return 'Предчистовая'
    if 'shell' in t:
        return v                      # официальное название сохраняем как есть
    if 'готов' in t or 'чистов' in t or 'с отделкой' in t:
        return 'Готовая отделка'
    return None                       # «Офис», «Торговля» и т.п. — не отделка, не выдумываем


def build(src, out_path=None):
    """Сырой xlsx -> таблица в 39 колонок. Возвращает (путь, статистика сопоставления)."""
    rwb = openpyxl.load_workbook(src, data_only=True)
    raw = list(rwb['Лоты (сырые)'].iter_rows(values_only=True))
    rh, rows = raw[0], raw[1:]
    R = {n: i for i, n in enumerate(rh)}
    report = list(rwb['Отчёт'].iter_rows(values_only=True))

    swb = openpyxl.load_workbook(svod_path(), data_only=True, read_only=True)
    q = list(swb['Продажа Q3 NEW'].iter_rows(values_only=True))
    qh = {n: i for i, n in enumerate(q[0]) if n}
    meta, q3lots = {}, collections.defaultdict(list)
    for r in q[1:]:
        if r[0] is None:
            continue
        k = (int(r[0]), str(r[1]).zfill(2) if r[1] is not None else '01')
        meta.setdefault(k, r)
        q3lots[k].append(r)
    g = lambda r, name: r[qh[name]] if name in qh else None

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Продажа'
    ws.append(COLS)
    today = datetime.date.today()
    bad = PatternFill('solid', fgColor='F8CBAD')
    flags_rows, matched = [], []
    now_by_key = collections.defaultdict(list)
    for r in rows:
        if r[0] is None:
            continue
        k = (int(r[R['project_id']]), str(r[R['sub_id']]))
        m = meta.get(k)
        row = [None] * 39
        put = lambda name, v: row.__setitem__(IDX[name] - 1, v)
        put('ID проекта', k[0]); put('SubID корпуса', k[1]); put('ID лота', r[R['lot_id']])
        if m:
            for name in ('Девелопер', 'Название проекта', 'Название корпуса', 'Класс', 'Адрес', 'Квартал ввода',
                         'Год ввода', 'Введен / не введен', 'Общая площадь проекта', 'Площадь офисов проекта',
                         'Общая площадь корпуса', 'Площадь офисов корпуса', 'Округ', 'Район', 'Зона', 'Субрынок',
                         'Широта', 'Долгота'):
                put(name, g(m, name))
        else:
            put('Название проекта', r[R['project']]); put('Название корпуса', r[R['corpus']])
        put('Здание/блок', 'Блок')
        put('Статус', 'В продаже')
        put('Площадь лота', r[R['area']]); put('Этаж', r[R['floor']])
        put('Отделка', finish_label(r[R['finish']]))
        n = ws.max_row + 1
        put('Стоимость лота с НДС', r[R['price_total']])
        put('Цена лота без НДС', f'=IF(Z{n}="","",IF(V{n}="ДДУ",Z{n},IF(AA{n}="","",Z{n}/(1+AA{n}))))')
        put('Цена лота руб./кв.м безНДС', f'=IF(OR(W{n}="",S{n}=""),"",W{n}/S{n})')
        put('НДС', f'=IF(OR(V{n}="ДКП",V{n}="ДКПБВ"),0.22,"")')
        put('Дата', today)
        put('Ссылка', r[R['source']])
        ws.append(row)
        if r[R['flags']]:
            bits = r[R['flags']]
            flags_rows.append([k[0], k[1], row[IDX['Название проекта'] - 1], r[R['lot_id']], bits])
            if 'нет цены' in bits or 'нет площади' in bits:
                for c in ws[n]:
                    c.fill = bad
        now_by_key[k].append((n, r[R['area']], r[R['floor']], r[R['price_total']], r[R['lot_id']]))

    for c in ws[1]:
        c.font = Font(bold=True)
        c.alignment = Alignment(wrap_text=True, vertical='top')
    ws.freeze_panes = 'A2'
    fmt = {'Площадь лота': '#,##0.0', 'Стоимость лота с НДС': '#,##0', 'Цена лота без НДС': '#,##0',
           'Цена лота руб./кв.м безНДС': '#,##0', 'НДС': '0%', 'Дата': 'DD.MM.YYYY'}
    for name, f in fmt.items():
        for c in ws[get_column_letter(IDX[name])][1:]:
            c.number_format = f
    for i, w in enumerate([9, 8, 16, 22, 26, 22, 10, 7, 30, 9, 8, 11, 14, 11, 11, 11, 11, 11, 10, 7, 14, 10, 14,
                           14, 6, 15, 7, 14, 14, 12, 16, 10, 10, 11, 8, 8, 8, 8, 40], 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # --- сопоставление лотов Q3 -> сейчас: по (корпус, площадь, этаж), кратные совпадения по очереди
    cmp_ws = wb.create_sheet('Сопоставление с Q3')
    cmp_ws.append(['ID проекта', 'SubID', 'Проект', 'Результат', 'ID лота Q3', 'Площадь Q3', 'Этаж Q3',
                   'Цена Q3 с НДС', 'ID лота сейчас', 'Площадь сейчас', 'Этаж сейчас', 'Цена сейчас с НДС',
                   'Δ цены, %'])
    stats = collections.defaultdict(lambda: collections.Counter())
    keyf = lambda a, f: (round(float(a), 1) if a not in (None, '') else None, str(f).strip() if f not in (None, '') else '')
    for k in sorted(set(now_by_key) | {k for k in q3lots if k in now_by_key}):
        pool = collections.defaultdict(list)
        for (n, a, f, p, lid) in now_by_key[k]:
            pool[keyf(a, f)].append((a, f, p, lid))
        name = g(meta[k], 'Название проекта') if k in meta else str(k)
        for ql in q3lots.get(k, []):
            if g(ql, 'Тип записи') == 'Без цены' or g(ql, 'Здание/блок') == 'Здание':
                continue
            kk = keyf(g(ql, 'Площадь лота'), g(ql, 'Этаж'))
            qp = g(ql, 'Стоимость лота с НДС')
            if pool.get(kk):
                a, f, p, lid = pool[kk].pop(0)
                d = round((p - qp) / qp * 100, 1) if p and qp else None
                res = 'сопоставлен' if d in (None, 0, 0.0) else ('цена изменилась')
                cmp_ws.append([k[0], k[1], name, res, g(ql, 'ID лота'), g(ql, 'Площадь лота'), g(ql, 'Этаж'), qp,
                               lid, a, f, p, d])
                stats[k][res] += 1
            else:
                cmp_ws.append([k[0], k[1], name, 'ушёл из продажи', g(ql, 'ID лота'), g(ql, 'Площадь лота'),
                               g(ql, 'Этаж'), qp])
                stats[k]['ушёл из продажи'] += 1
        for kk, left in pool.items():
            for a, f, p, lid in left:
                cmp_ws.append([k[0], k[1], name, 'новый', None, None, None, None, lid, a, f, p])
                stats[k]['новый'] += 1
    cmp_ws.freeze_panes = 'A2'
    for c in cmp_ws[1]:
        c.font = Font(bold=True)

    # --- отчёт по корпусам + что не выгружено
    rep = wb.create_sheet('Отчёт по корпусам')
    rep.append(['ID проекта', 'SubID', 'Проект', 'Корпус', 'Лотов сейчас', 'Лотов Q3', 'Площадь сейчас, м²',
                'Площадь Q3, м²', 'Без цены', 'Без площади', 'Сопоставлено', 'Цена изменилась', 'Новых',
                'Ушло', 'Замечание'])
    done = set()
    for row in report[1:]:
        k = (int(row[0]), str(row[1]))
        done.add(k)
        s = stats.get(k, collections.Counter())
        rep.append([row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9],
                    s['сопоставлен'], s['цена изменилась'], s['новый'], s['ушёл из продажи'], row[10]])
    reg = list(csv.DictReader(open(HERE / 'registry_q3.csv', encoding='utf-8-sig'), delimiter=';'))
    rep.append([])
    rep.append(['НЕ ВЫГРУЖЕНО (нужна ручная выгрузка или другая сеть)'])
    for r in reg:
        k = (int(r['project_id']), r['sub_id'])
        if k in done:
            continue
        dom = r['domain']
        why = 'сайт не отвечает с этой сети' if dom else 'нет сайта застройщика (данные из прайса/по запросу)'
        if dom in ('www.mr-group.ru',):
            why = 'сайт отвечает 403 (защита), только вручную через браузер'
        rep.append([r['project_id'], r['sub_id'], r['project'], r['corpus'], None, r['q3_lots'], None,
                    r['q3_area'], None, None, None, None, None, None, f'{why} ({dom or "—"})'])
    for c in rep[1]:
        c.font = Font(bold=True)
    rep.freeze_panes = 'A2'

    fl = wb.create_sheet('Пометки по лотам')
    fl.append(['ID проекта', 'SubID', 'Проект', 'ID лота', 'Пометка'])
    for r in flags_rows:
        fl.append(r)
    for c in fl[1]:
        c.font = Font(bold=True)

    chk = wb.create_sheet('База для проверки')
    chk.append(['ID проекта', 'SubID', 'Проект', 'Корпус', 'Фаза проекта (Q3, не проверена)',
                'Схема продажи (Q3, не проверена)', 'Квартал ввода', 'Год ввода', 'Введен / не введен'])
    for k in sorted(done):
        m = meta.get(k)
        if m:
            chk.append([k[0], k[1], g(m, 'Название проекта'), g(m, 'Название корпуса'), g(m, 'Фаза проекта'),
                        g(m, 'Схема продажи (исходная)') or g(m, 'Схема продажи'), g(m, 'Квартал ввода'),
                        g(m, 'Год ввода'), g(m, 'Введен / не введен')])
    for c in chk[1]:
        c.font = Font(bold=True)

    out = str(out_path) if out_path else str(HERE / 'out' / f'Лоты_39_колонок_{today.strftime("%d.%m.%Y")}.xlsx')
    wb.save(out)
    tot = collections.Counter()
    for st in stats.values():
        tot.update(st)
    return out, {'lots': ws.max_row - 1, 'compare': dict(tot)}


if __name__ == '__main__':
    o, st = build(raw_path())
    print('Файл:', o, st)
