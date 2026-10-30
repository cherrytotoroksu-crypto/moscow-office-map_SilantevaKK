"""peredelkino-offices.ru (Родина Переделкино): серверный HTML, карточки .cards-container a.card."""
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
    cards = BeautifulSoup(html, 'lxml').select('.cards-container a.card')
    for c in cards:
        txt = c.get_text(' | ', strip=True).replace('\xa0', ' ')
        m_n = re.match(r'№\s*([\w/]+)', txt)
        m_f = re.search(r'(\d+)\s*этаж', txt)
        m_a = re.search(r'([\d.,]+)\s*м²', txt)
        m_p = re.search(r'([\d ]{6,})\s*₽', txt)
        href = c.get('href', '')
        r.add(lot_id=m_n.group(1) if m_n else None, lot_name=txt[:60], area=num(m_a.group(1)) if m_a else None,
              floor=int(m_f.group(1)) if m_f else None, status='В продаже',
              price_total=num(m_p.group(1)) if m_p else None,
              url=('https://peredelkino-offices.ru' + href) if href.startswith('/') else (href or t['url']))
    if not cards:
        r.notes.append('карточки не найдены')
    return r
