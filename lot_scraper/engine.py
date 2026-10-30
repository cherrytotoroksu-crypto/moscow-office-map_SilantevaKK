"""Движок выгрузки лотов: каталог корпусов, запуск парсеров, сырой xlsx, таблица в 39 колонок.
Используется веб-интерфейсом (server.py + scraper.html) и командной строкой:
    python engine.py --all            выгрузить всё, что есть парсер
    python engine.py 216|04 279|02    только перечисленные корпуса (project_id|sub_id)
"""
import sys, csv, time, datetime, importlib, threading, concurrent.futures as cf
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out'
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / 'sites'))

from core import FIELDS, Result          # noqa: E402
from targets import T                     # noqa: E402

WORKERS = 6


# в реестре Q3 один девелопер записан по-разному (латиница/кириллица, бренд/группа) — для интерфейса сводим
DEV_ALIAS = {'A101': 'А101', 'AFI Девелопмент': 'AFI Development', 'ГК Пионер': 'Пионер', 'PIONEER': 'Пионер',
             'Группа Родина': 'Родина'}


def key_of(pid, sub):
    return f'{int(pid)}|{sub}'


def ensure_registry():
    if not (HERE / 'registry_q3.csv').exists():
        import make_registry
        make_registry.build()


def catalog():
    """Все корпуса из реестра Q3 + признак, есть ли парсер."""
    ensure_registry()
    parsers = {key_of(t['project_id'], t['sub_id']): t for t in T}
    rows = []
    with open(HERE / 'registry_q3.csv', encoding='utf-8-sig') as f:
        for r in csv.DictReader(f, delimiter=';'):
            k = key_of(r['project_id'], r['sub_id'])
            t = parsers.get(k)
            if t:
                note = ''
            elif r['domain']:
                note = 'парсера пока нет (сайт ' + r['domain'] + ')'
            else:
                note = 'нет сайта застройщика: данные из прайса / по запросу'
            rows.append({'key': k, 'project_id': int(r['project_id']), 'sub_id': r['sub_id'],
                         'developer': DEV_ALIAS.get(r['developer'], r['developer']), 'project': r['project'], 'corpus': r['corpus'],
                         'q3_lots': int(r['q3_lots']), 'q3_area': float(r['q3_area']), 'domain': r['domain'],
                         'url': r['url'], 'has_parser': bool(t), 'site': t['site'] if t else None, 'note': note})
    return rows


def _run_one(t):
    # сети нестабильны: при ошибке повторяем парсер до 3 раз
    for attempt in range(3):
        try:
            r = importlib.import_module(t['site']).run(t)
        except Exception as e:                      # noqa: BLE001 - парсер не должен ронять весь запуск
            r = Result(t)
            r.error = f'сбой парсера: {e}'
        if not r.error:
            break
        time.sleep(4 * (attempt + 1))
    return r


def run_targets(targets, on_update=None):
    """Запустить парсеры для targets (элементы targets.T). on_update(key, state, result|None) для прогресса."""
    emit = on_update or (lambda *a: None)
    results = {}

    def work(t):
        k = key_of(t['project_id'], t['sub_id'])
        emit(k, 'running', None)
        r = _run_one(t)
        results[k] = r
        emit(k, 'error' if r.error else 'done', r)
        return k

    with cf.ThreadPoolExecutor(WORKERS) as ex:
        list(ex.map(work, targets))
    # второй проход: упавшие корпуса по одному, когда нагрузка спала
    for t in targets:
        k = key_of(t['project_id'], t['sub_id'])
        if results[k].error:
            emit(k, 'retry', None)
            time.sleep(8)
            r2 = _run_one(t)
            if not r2.error:
                r2.notes.append('получено со второго прохода')
            results[k] = r2
            emit(k, 'error' if r2.error else 'done', r2)
    return [results[key_of(t['project_id'], t['sub_id'])] for t in targets]


def write_raw(results, path):
    """Сырой xlsx: лист «Лоты (сырые)» + «Отчёт» (сверка с Q3)."""
    import openpyxl
    from openpyxl.styles import Font
    ensure_registry()
    q3 = {}
    with open(HERE / 'registry_q3.csv', encoding='utf-8-sig') as f:
        for r in csv.DictReader(f, delimiter=';'):
            q3[(int(r['project_id']), r['sub_id'])] = (int(r['q3_lots']), float(r['q3_area']))
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Лоты (сырые)'
    ws.append(FIELDS)
    rep = wb.create_sheet('Отчёт')
    rep.append(['ID проекта', 'SubID', 'Проект', 'Корпус', 'Лотов сейчас', 'Лотов Q3', 'Площадь сейчас',
                'Площадь Q3', 'Без цены', 'Без площади', 'Замечание'])
    for sh in (ws, rep):
        for c in sh[1]:
            c.font = Font(bold=True)
    for r in results:
        for lot in r.lots:
            ws.append([lot[f] for f in FIELDS])
        n = len(r.lots)
        area = sum(lot['area'] or 0 for lot in r.lots)
        q = q3.get((int(r.t['project_id']), r.t['sub_id']), (None, None))
        msg = []
        if r.error:
            msg.append('ОШИБКА: ' + r.error)
        elif n == 0:
            msg.append('0 лотов: проверить вручную')
        elif q[0] and abs(n - q[0]) / q[0] > 0.3:
            msg.append(f'число лотов изменилось сильно (Q3 {q[0]} -> {n})')
        msg += r.notes
        rep.append([r.t['project_id'], r.t['sub_id'], r.t['project'], r.t['corpus'], n, q[0], round(area, 1), q[1],
                    sum(1 for lot in r.lots if not lot['price_total']), sum(1 for lot in r.lots if not lot['area']),
                    '; '.join(msg)])
    ws.freeze_panes = 'A2'
    wb.save(path)


def export(results, label=''):
    """Результаты -> (сырой xlsx, таблица 39 колонок). Возвращает имена файлов в out/ и сводку."""
    import build_39
    OUT.mkdir(exist_ok=True)
    stamp = datetime.datetime.now().strftime('%d.%m.%Y_%H%M')
    raw = OUT / f'lots_raw_{stamp}{label}.xlsx'
    write_raw(results, raw)
    table, st = build_39.build(str(raw), OUT / f'Лоты_39_колонок_{stamp}{label}.xlsx')
    return raw.name, Path(table).name, st


def summary(results):
    return {'buildings': len(results), 'ok': sum(1 for r in results if not r.error),
            'errors': sum(1 for r in results if r.error), 'lots': sum(len(r.lots) for r in results),
            'no_price': sum(1 for r in results for lot in r.lots if not lot['price_total']),
            'no_area': sum(1 for r in results for lot in r.lots if not lot['area'])}


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)
    chosen = T if args == ['--all'] else [t for t in T if key_of(t['project_id'], t['sub_id']) in args]
    if not chosen:
        sys.exit('Нет парсеров для указанных корпусов')
    res = run_targets(chosen, lambda k, s, r: print(k, s, (len(r.lots) if r else '')))
    raw, table, st = export(res, '' if args == ['--all'] else '_выборка')
    print(summary(res))
    print('Файлы в', OUT, ':', raw, table)
