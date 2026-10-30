"""air.pro: список офисов li.offices-list, подгрузка прокруткой/кнопкой, рендер в браузере."""
import re
from bs4 import BeautifulSoup
from core import num, Result
from browser import render

SEL = '.offices-list > li:not(.js-ajax-list-promo)'


def run(t):
    r = Result(t)
    try:
        html = render('https://air.pro/offices', SEL, click='.js-load-more a.btn')
    except Exception as e:
        r.error = f'{type(e).__name__}: {str(e)[:80]}'
        return r
    for li in BeautifulSoup(html, 'lxml').select(SEL):
        txt = li.get_text(' | ', strip=True).replace('\xa0', ' ')
        m_c = re.search(r'Корпус\s*(\d+)', txt)
        if m_c and f"Корпус {m_c.group(1)}" != t['air_corpus']:
            continue
        m_n = re.search(r'офис\s*№\s*(\d+)', txt, re.I)
        m_a = re.search(r'([\d.,]+)\s*м\b', txt)
        m_f = re.search(r'Этаж\s*(\d+)', txt)
        m_p = re.findall(r'([\d ]{6,})\s*₽', txt)
        a = li.find('a', href=True)
        r.add(lot_id=m_n.group(1) if m_n else None, lot_name=txt[:60], area=num(m_a.group(1)) if m_a else None,
              floor=int(m_f.group(1)) if m_f else None, status='В продаже',
              price_total=num(m_p[-1]) if m_p else None,
              url=('https://air.pro' + a['href']) if a and a['href'].startswith('/') else t['url'])
    return r
