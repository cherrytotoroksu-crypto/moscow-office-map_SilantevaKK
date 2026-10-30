"""Общее ядро выгрузки лотов: схема, загрузка с повторами, разбор чисел, отчёт."""
import re, time, datetime, requests

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0'
HEAD = {'User-Agent': UA, 'Accept-Language': 'ru'}
FIELDS = ['project_id', 'sub_id', 'project', 'corpus', 'lot_id', 'lot_name', 'area', 'floor',
          'finish', 'status', 'price_total', 'price_m2', 'url', 'source', 'collected', 'flags']


def num(s):
    """'33 837 650 ₽' -> 33837650.0; '56,9' -> 56.9; не число -> None"""
    if s is None:
        return None
    t = re.sub(r'[^\d,.\-]', '', str(s).replace('\xa0', '').replace(' ', ''))
    t = t.replace(',', '.')
    if t.count('.') > 1:
        t = t.replace('.', '', t.count('.') - 1)
    try:
        return float(t) if t not in ('', '.', '-') else None
    except ValueError:
        return None


def get(url, retries=3, timeout=25, headers=None, **kw):
    last = None
    for i in range(retries):
        try:
            r = requests.get(url, headers={**HEAD, **(headers or {})}, timeout=timeout, **kw)
            if r.status_code == 200:
                return r
            last = f'HTTP {r.status_code}'
        except Exception as e:
            last = type(e).__name__
        time.sleep(1.5 * (i + 1))
    raise RuntimeError(f'{url}: {last}')


class Result:
    """Результат по одному корпусу: лоты + замечания."""
    def __init__(self, target):
        self.t = target
        self.lots = []
        self.notes = []
        self.error = None
        self.stale = None
        self.prev = None

    def add(self, **kw):
        row = {k: None for k in FIELDS}
        row.update(project_id=self.t['project_id'], sub_id=self.t['sub_id'], project=self.t['project'],
                   corpus=self.t['corpus'], source=self.t['url'],
                   collected=datetime.date.today().isoformat())
        row.update(kw)
        flags = []
        if not row['area']:
            flags.append('нет площади')
        if not row['price_total']:
            flags.append('нет цены')
        if row['area'] and row['price_total'] and not row['price_m2']:
            row['price_m2'] = round(row['price_total'] / row['area'])
        if row['area'] and row['price_total'] and row['price_m2']:
            if abs(row['price_total'] / row['area'] - row['price_m2']) / row['price_m2'] > 0.03:
                flags.append('цена и ₽/м² не сходятся')
        row['flags'] = '; '.join(flags + ([row['flags']] if row['flags'] else []))
        self.lots.append(row)
