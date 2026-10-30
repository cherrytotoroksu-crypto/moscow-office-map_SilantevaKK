"""geolog2.moscow: строки div.offices__row, кнопка «показать ещё», рендер в браузере."""
import re
from bs4 import BeautifulSoup
from core import num, Result
from browser import render

SEL = 'div.offices__row'


def run(t):
    r = Result(t)
    try:
        html = render('https://geolog2.moscow/', SEL, scroll=False, click='.offices__list-more button')
    except Exception as e:
        r.error = f'{type(e).__name__}: {str(e)[:80]}'
        return r
    for row in BeautifulSoup(html, 'lxml').select(SEL):
        txt = row.get_text(' | ', strip=True).replace('\xa0', ' ')
        m_n = re.search(r'№\s*([\d.]+)', txt)
        m_f = re.search(r'(\d+)\s*этаж', txt)
        m_a = re.search(r'([\d,.]+)\s*м²', txt)
        prices = [num(x) for x in re.findall(r'([\d ]{6,})\s*₽', txt)]
        flags = None
        total = ppm = None
        if len(prices) >= 3:
            ppm, total = prices[0], prices[1]       # ₽/м², цена лота
            flags = f'вторая цена на сайте {int(prices[2]):,}'.replace(',', ' ')
        elif prices:
            total = prices[0]
        r.add(lot_id=m_n.group(1) if m_n else None, lot_name=txt[:40], area=num(m_a.group(1)) if m_a else None,
              floor=int(m_f.group(1)) if m_f else None, status='В продаже', price_total=total, price_m2=ppm,
              url=t['url'], flags=flags)
    return r
