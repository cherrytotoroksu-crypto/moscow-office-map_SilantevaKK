"""Движок выгрузки лотов: каталог корпусов, запуск парсеров, сырой xlsx, таблица в 39 колонок.
Используется веб-интерфейсом (server.py + scraper.html) и командной строкой:
    python engine.py --all            выгрузить всё, что есть парсер
    python engine.py 216|04 279|02    только перечисленные корпуса (project_id|sub_id)
"""
import sys, csv, json, time, socket, statistics, datetime, importlib, threading, concurrent.futures as cf
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out'
HISTORY = HERE / 'history'      # последний удачный результат по каждому корпусу (в git не попадает)
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


def _hist_path(t):
    return HISTORY / (key_of(t['project_id'], t['sub_id']).replace('|', '_') + '.json')


def load_last(t):
    try:
        return json.loads(_hist_path(t).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def save_last(r):
    if r.error or not r.lots:
        return
    HISTORY.mkdir(exist_ok=True)
    _hist_path(r.t).write_text(json.dumps({'date': datetime.date.today().isoformat(), 'lots': r.lots},
                                          ensure_ascii=False), encoding='utf-8')


def _fmt_date(iso):
    y, m, d = iso.split('-')
    return f'{d}.{m}.{y}'


def preflight(targets, timeout=6):
    """Какие домены отвечают (TCP :443). {домен: True/False}. Не обходит ничего, просто проверка связи."""
    hosts = sorted({urlparse(t['url']).hostname for t in targets if t.get('url')})

    def ping(h):
        try:
            socket.create_connection((h, 443), timeout=timeout).close()
            return h, True
        except OSError:
            return h, False
    with cf.ThreadPoolExecutor(16) as ex:
        return dict(ex.map(ping, hosts))


def stale_fallback(r):
    """Сайт не ответил: берём последний удачный результат с пометкой, чтобы корпус не пропал из таблицы."""
    last = load_last(r.t)
    if not last or not last.get('lots'):
        return r
    r.lots = last['lots']
    for lot in r.lots:
        lot['flags'] = ((lot.get('flags') or '') + '; ' if lot.get('flags') else '') + f'УСТАРЕВШИЕ ДАННЫЕ от {_fmt_date(last["date"])}'
    r.notes.append(f'УСТАРЕЛО: сайт не ответил ({r.error}); показаны данные последней удачной выгрузки от {_fmt_date(last["date"])}')
    r.stale = last['date']
    r.error = None
    return r


M2_MIN, M2_MAX = 40_000, 2_500_000      # коридор ₽/м² для офисов; вне него — подозрение на ошибку разбора


def check_anomalies(r, prev=None):
    """Пометки о подозрительных данных. prev — прошлая удачная выгрузка (до этого запуска)."""
    if r.error or getattr(r, 'stale', None):
        return
    n = len(r.lots)
    if n == 0:
        r.notes.append('0 лотов: вёрстка могла измениться или лотов нет, проверить вручную')
        return
    bad = 0
    for lot in r.lots:
        m2 = lot.get('price_m2')
        if m2 and not (M2_MIN <= m2 <= M2_MAX):
            lot['flags'] = ((lot['flags'] + '; ') if lot['flags'] else '') + f'₽/м² вне коридора {M2_MIN:,}–{M2_MAX:,}'.replace(',', ' ')
            bad += 1
    if bad:
        r.notes.append(f'{bad} лотов с ₽/м² вне разумного коридора: проверить разбор цены/площади')
    if prev and prev.get('lots'):
        pn = len(prev['lots'])
        if pn and abs(n - pn) / pn > 0.3:
            r.notes.append(f'число лотов изменилось сильно относительно прошлой выгрузки от {_fmt_date(prev["date"])}: {pn} -> {n}')
        a = [l['price_m2'] for l in prev['lots'] if l.get('price_m2')]
        b = [l['price_m2'] for l in r.lots if l.get('price_m2')]
        if len(a) >= 3 and len(b) >= 3:
            ma, mb = statistics.median(a), statistics.median(b)
            if abs(mb - ma) / ma > 0.25:
                r.notes.append(f'медианный ₽/м² изменился на {round((mb - ma) / ma * 100)}% с прошлой выгрузки ({round(ma):,} -> {round(mb):,})'.replace(',', ' '))


def _run_one(t, dead=False):
    # сети нестабильны: при ошибке повторяем парсер до 3 раз
    for attempt in range(1 if dead else 3):
        try:
            r = importlib.import_module(t['site']).run(t)
        except Exception as e:                      # noqa: BLE001 - парсер не должен ронять весь запуск
            r = Result(t)
            r.error = f'сбой парсера: {e}'
        if not r.error:
            break
        time.sleep(4 * (attempt + 1))
    if r.error and dead:
        r.error = 'домен не отвечает (проверка связи)'
    return r


def run_targets(targets, on_update=None):
    """Запустить парсеры для targets (элементы targets.T). on_update(key, state, result|None) для прогресса.
    Перед запуском проверяется связь с доменами (мёртвые не мучаем повторами), после — контроль аномалий;
    если сайт не ответил, берётся последняя удачная выгрузка с пометкой «устарело»."""
    emit = on_update or (lambda *a: None)
    alive = preflight(targets)
    dead = lambda t: not alive.get(urlparse(t['url']).hostname, True)     # noqa: E731
    results = {}
    prevs = {key_of(t['project_id'], t['sub_id']): load_last(t) for t in targets}

    def finish(k, r):
        results[k] = r
        if r.error:
            r = stale_fallback(r)
            results[k] = r
        else:
            check_anomalies(r, prevs[k])
            save_last(r)
        emit(k, 'stale' if getattr(r, 'stale', None) else 'error' if r.error else 'done', r)

    def work(t):
        k = key_of(t['project_id'], t['sub_id'])
        emit(k, 'running', None)
        r = _run_one(t, dead(t))
        results[k] = r
        if r.error:
            emit(k, 'error', r)               # промежуточно: покажем ошибку, второй проход ещё впереди
        else:
            finish(k, r)
        return k

    with cf.ThreadPoolExecutor(WORKERS) as ex:
        list(ex.map(work, targets))
    # второй проход: упавшие корпуса по одному, когда нагрузка спала (мёртвые домены пропускаем)
    for t in targets:
        k = key_of(t['project_id'], t['sub_id'])
        if results[k].error:
            if not dead(t):
                emit(k, 'retry', None)
                time.sleep(8)
                r2 = _run_one(t)
                if not r2.error:
                    r2.notes.append('получено со второго прохода')
                    results[k] = r2
            finish(k, results[k])
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
            'errors': sum(1 for r in results if r.error), 'stale': sum(1 for r in results if r.stale), 'lots': sum(len(r.lots) for r in results),
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
