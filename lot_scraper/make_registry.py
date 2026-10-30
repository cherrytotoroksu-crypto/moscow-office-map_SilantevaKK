"""Строит registry_q3.csv (список всех корпусов Q3: ID, девелопер, проект, корпус, число/площадь лотов, сайт)
из свода Q3 2026. Файл в git не хранится (внутренние данные), создаётся автоматически при первом запуске."""
import csv, collections, urllib.parse
from pathlib import Path
import openpyxl
import build_39

HERE = Path(__file__).resolve().parent


def build():
    wb = openpyxl.load_workbook(build_39.svod_path(), data_only=True, read_only=True)
    rows = list(wb['Продажа Q3 NEW'].iter_rows(values_only=True))
    h = rows[0]
    L = h.index('Ссылка')
    g = collections.OrderedDict()
    for r in rows[1:]:
        if r[0] is None:
            continue
        d = g.setdefault((r[0], r[1]), dict(dev=r[3], proj=r[4], corp=r[5], n=0, area=0, links=collections.Counter()))
        d['n'] += 1
        d['area'] += r[18] or 0
        d['links'][r[L]] += 1
    key = lambda kv: (urllib.parse.urlparse(kv[1]['links'].most_common(1)[0][0] or '').netloc, kv[0][0])
    with open(HERE / 'registry_q3.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['project_id', 'sub_id', 'developer', 'project', 'corpus', 'q3_lots', 'q3_area', 'domain', 'url'])
        for (a, b), d in sorted(g.items(), key=key):
            link = d['links'].most_common(1)[0][0] or ''
            dom = urllib.parse.urlparse(link).netloc if link.startswith('http') else ''
            w.writerow([a, b, d['dev'], d['proj'], d['corp'], d['n'], round(d['area'], 1), dom, link])


if __name__ == '__main__':
    build()
    print('registry_q3.csv обновлён')
