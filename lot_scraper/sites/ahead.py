"""aheadmoscow.ru: серверный HTML, строки .shoplist__item, берём тип Office."""
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
    for row in BeautifulSoup(html, 'lxml').select('.shoplist__item:not(.shoplist__table_head)'):
        txt = [x for x in row.get_text('|', strip=True).split('|') if x]
        line = ' | '.join(txt)
        if 'Office' not in line:
            r.notes.append(f'не офис: {line[:40]}')
            continue
        m_a = re.search(r'([\d,]+)\s*\|\s*м²', line)
        m_f = re.search(r'(\d+)\s*\|\s*этаж', line)
        m_p = re.search(r'([\d ]{6,})\s*\|?\s*руб', line.replace('\xa0', ' '))
        a = row.find('a', href=True)
        r.add(lot_id=txt[0], lot_name=line[:60], area=num(m_a.group(1)) if m_a else None,
              floor=int(m_f.group(1)) if m_f else None, status='В продаже',
              price_total=num(m_p.group(1)) if m_p else None,
              url=('https://aheadmoscow.ru' + a['href']) if a and a['href'].startswith('/') else t['url'])
    return r
