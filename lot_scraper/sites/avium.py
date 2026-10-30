"""avium.ru: серверный HTML, строки div.table-row-content; берём офисы нужного корпуса."""
import re
from bs4 import BeautifulSoup
from core import get, num, Result


def run(t):
    r = Result(t)
    try:
        html = get(t['url']).text
    except Exception as e:
        r.error = str(e)
        return r
    for row in BeautifulSoup(html, 'lxml').select('div.table-row-content'):
        txt = [x for x in row.get_text('|', strip=True).split('|') if x]
        line = ' | '.join(txt)
        m_b = re.search(r'Корпус\s*\|\s*(\d+)', line)
        if m_b and m_b.group(1) != str(t['avium_building']):
            continue
        if re.search(r'ритейл|кладов|машино|апарт', line, re.I):
            continue
        m_f = re.search(r'(\d+)\s+из\s+\d+', line)
        m_a = re.search(r'([\d.,]+)\s*м²', line)
        m_n = re.search(r'№\s*\|\s*([\w.\-]+)', line)
        nums = [num(x) for x in txt if re.fullmatch(r'[\d ]{6,}', x.replace('\xa0', ' '))]
        a = row.select_one("a[href*='ofis']") or row.find('a')
        r.add(lot_id=m_n.group(1) if m_n else None, lot_name=line[:80],
              area=num(m_a.group(1)) if m_a else None,
              floor=int(m_f.group(1)) if m_f else None, status='В продаже',
              price_total=max(nums) if nums else None,
              url=('https://avium.ru' + a['href']) if a and a['href'].startswith('/') else t['url'])
    return r
