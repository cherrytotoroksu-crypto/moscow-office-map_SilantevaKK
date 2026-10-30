"""granelle.ru (Звенигородская от Гранель): серверный HTML, карточки article.FlatsCard*.
На карточке две цены: «от X» со скидкой -5% и зачёркнутая прайсовая. Берём цену «от» (она стоит
в заголовке карточки и совпадает с «цена за м²»), прайсовую пишем в flags."""
import re
from bs4 import BeautifulSoup
from core import get, num, Result


def run(t):
    r = Result(t)
    try:
        html = get(t['url'], timeout=40).text
    except Exception as e:
        r.error = str(e)
        return r
    for c in BeautifulSoup(html, 'lxml').select('article[class*=FlatsCard]'):
        txt = c.get_text(' | ', strip=True).replace('\xa0', ' ')
        if t['granelle_name'] not in txt:
            continue
        if not txt.startswith('Офис'):
            r.notes.append('не офис: ' + txt[:30])
            continue
        m_a = re.search(r'([\d.]+)\s*м\b', txt)
        m_f = re.search(r'Этаж\s*(\d+)', txt)
        m_p = re.search(r'от\s*([\d ]+)\s*₽', txt)
        m_old = re.search(r'-\s*\d+%\s*\|\s*([\d ]+)\s*₽', txt)
        m_ppm = re.search(r'цена за м²:\s*([\d ]+)', txt)
        a = c.find('a', href=True)
        r.add(lot_id=(a['href'].rstrip('/').split('/')[-1] if a else None), lot_name='Офис',
              area=num(m_a.group(1)) if m_a else None, floor=int(m_f.group(1)) if m_f else None,
              finish='Shell&Core' if 'Shell' in txt else None, status='В продаже',
              price_total=num(m_p.group(1)) if m_p else None,
              price_m2=num(m_ppm.group(1)) if m_ppm else None,
              url=('https://granelle.ru' + a['href']) if a and a['href'].startswith('/') else t['url'],
              flags=f'прайсовая цена без скидки {num(m_old.group(1)):.0f}' if m_old else None)
    return r
